"""
whatsapp/router.py — Meta WhatsApp webhook endpoint'leri.

GET  /whatsapp/webhook  → Meta'nın webhook doğrulaması (hub.challenge)
POST /whatsapp/webhook  → Gelen mesajlar (metin, buton, liste yanıtı)

Meta webhook doğrulama akışı:
  1. Meta, GET isteği gönderir: ?hub.mode=subscribe&hub.challenge=xxx&hub.verify_token=yyy
  2. hub.verify_token, .env'deki WA_VERIFY_TOKEN ile eşleşirse hub.challenge döndürülür.
  3. Eşleşmezse 403 döner.

Gelen mesaj yapısı:
  POST gövdesi: {"entry": [{"changes": [{"value": {"messages": [...], "metadata": {...}}}]}]}

TenantMiddleware bu route'da tenant zorunluluğunu ATLAR çünkü
/api/v1/whatsapp/* superadmin benzeri tenant-serbest route olarak çalışır.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.tenant import Tenant
from app.modules.whatsapp.handlers import handle_incoming
from app.modules.whatsapp.tracking import log_wa_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


# ─── Webhook Doğrulama (GET) ──────────────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Meta'nın webhook doğrulama isteğini yanıtlar.

    Meta dashboard'a webhook URL girildiğinde bu endpoint bir kez çağrılır.
    hub.verify_token == WA_VERIFY_TOKEN ise hub.challenge plain text döner.
    """
    settings = get_settings()

    if hub_mode != "subscribe":
        raise HTTPException(400, {"error": "invalid_hub_mode"})

    if not settings.wa_verify_token:
        logger.error("WA_VERIFY_TOKEN ayarlanmamış — webhook doğrulanamıyor")
        raise HTTPException(500, {"error": "verify_token_not_configured"})

    if hub_verify_token != settings.wa_verify_token:
        logger.warning("Webhook doğrulama başarısız — yanlış verify_token")
        raise HTTPException(403, {"error": "forbidden"})

    logger.info("WhatsApp webhook başarıyla doğrulandı")
    # Meta düz metin integer bekler
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(hub_challenge or "")


# ─── Gelen Mesajlar (POST) ────────────────────────────────────────────────────

@router.post("/webhook", status_code=200)
async def receive_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Meta'dan gelen mesajları alır ve bot akışını tetikler.

    Meta, her mesajda 200 OK beklediği için tüm işlem arka planda yapılır.
    Hata durumunda da 200 dönülür — Meta'nın retry storm'unu önlemek için.
    """
    try:
        body = await request.json()
    except Exception:
        # Geçersiz JSON → yine de 200 dön
        return {"status": "ok"}

    try:
        await _process_webhook(body, db)
    except Exception as exc:
        # İşleme hatası bot akışını durdurmamalı; Meta'ya hep 200 dön
        logger.error("Webhook işleme hatası | error=%s", exc, exc_info=True)
        await log_wa_error(db, "webhook_error", str(exc))

    return {"status": "ok"}


async def _process_webhook(body: dict, db: AsyncSession) -> None:
    """
    Webhook gövdesini ayrıştırır, mesajları handle_incoming'e yönlendirir.

    Meta webhook yapısı:
      body.entry[] → .changes[] → .value.messages[] + .value.metadata
    """
    if body.get("object") != "whatsapp_business_account":
        return

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Hangi WA numarasına mesaj geldi?
            metadata = value.get("metadata", {})
            phone_number_id = (metadata.get("phone_number_id") or "").strip()

            if not phone_number_id:
                continue

            await _log_status_errors(value, db, phone_number_id)

            tenant_result = await db.execute(
                select(Tenant).where(
                    Tenant.whatsapp_phone_number_id == phone_number_id,
                    Tenant.whatsapp_connection_status == "connected",
                    Tenant.is_active.is_(True),
                )
            )
            tenant = tenant_result.scalar_one_or_none()
            if tenant is None:
                await log_wa_error(
                    db,
                    "unknown_phone_number_id",
                    "WhatsApp phone_number_id icin tenant bulunamadi",
                    meta={"phone_number_id": phone_number_id},
                )
                continue

            # Gönderen profil adları (contacts listesinde)
            contacts = {
                c.get("wa_id"): c.get("profile", {}).get("name", "Musteri")
                for c in value.get("contacts", [])
                if c.get("wa_id")
            }

            for msg in value.get("messages", []):
                wa_phone = msg.get("from", "")
                wa_name = contacts.get(wa_phone, "Musteri")
                msg_type = msg.get("type", "")
                content: str | None = None

                if msg_type == "text":
                    content = msg.get("text", {}).get("body", "").strip()

                elif msg_type == "interactive":
                    interactive = msg.get("interactive", {})
                    itype = interactive.get("type", "")
                    if itype == "button_reply":
                        content = interactive.get("button_reply", {}).get("id", "")
                    elif itype == "list_reply":
                        content = interactive.get("list_reply", {}).get("id", "")

                else:
                    # Ses, görsel, konum vb. — şimdilik yoksay
                    logger.debug("Desteklenmeyen mesaj tipi: %s", msg_type)
                    continue

                if not wa_phone:
                    continue

                await handle_incoming(
                    wa_phone=wa_phone,
                    phone_number_id=phone_number_id,
                    wa_name=wa_name,
                    msg_type=msg_type,
                    content=content,
                    db=db,
                    tenant=tenant,
                )


async def _log_status_errors(value: dict, db: AsyncSession, phone_number_id: str) -> None:
    """Meta delivery/status webhook'larindaki hata detaylarini kayda alir."""
    for status in value.get("statuses", []):
        errors = status.get("errors") or []
        if not errors:
            continue
        await log_wa_error(
            db,
            "message_status_error",
            "WhatsApp mesaj status webhook hata bildirdi",
            wa_phone=status.get("recipient_id"),
            meta={
                "phone_number_id": phone_number_id,
                "message_id": status.get("id"),
                "status": status.get("status"),
                "errors": errors,
            },
        )
