"""
whatsapp/tracking.py — WA iletişim ve hata kaydı yardımcıları.

Her iki fonksiyon da fire-and-forget mantığıyla çalışır:
hata oluşursa yalnızca log yazılır, ana akış etkilenmez.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wa_contact_log import WaContactLog
from app.models.wa_error_log import WaErrorLog

logger = logging.getLogger(__name__)


async def log_wa_contact(
    db: AsyncSession,
    wa_phone: str,
    tenant_id: uuid.UUID,
) -> None:
    """
    Aynı (tenant, telefon, gün) için tekrarsız temas kaydı oluşturur.
    Aynı gün içinde birden fazla mesaj gelse de yalnızca bir satır oluşur.
    """
    try:
        today = datetime.now(timezone.utc).date()
        stmt = (
            pg_insert(WaContactLog)
            .values(tenant_id=tenant_id, wa_phone=wa_phone, contact_date=today)
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as exc:
        logger.warning("wa_contact_log yazma hatası | %s", exc)


async def log_wa_error(
    db: AsyncSession,
    error_type: str,
    message: str,
    tenant_id: uuid.UUID | None = None,
    wa_phone: str | None = None,
    meta: dict | None = None,
) -> None:
    """Bot hatasını wa_error_logs tablosuna yazar."""
    try:
        entry = WaErrorLog(
            tenant_id=tenant_id,
            wa_phone=wa_phone,
            error_type=error_type,
            message=message,
            meta_json=meta,
        )
        db.add(entry)
        await db.commit()
    except Exception as exc:
        logger.warning("wa_error_log yazma hatası | %s", exc)
