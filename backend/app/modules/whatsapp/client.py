"""
whatsapp/client.py — Meta Graph API ile mesaj gönderme.

Desteklenen mesaj türleri:
  send_text        → düz metin
  send_buttons     → maks 3 hızlı yanıt butonu (interactive button)
  send_list        → çok seçenekli liste (interactive list, bölümlü)

Her fonksiyon, ilgili tenant'ın phone_number_id ve access_token bilgisini alır.
Hata durumunda False döner — çağıranlar bunu kritik hata saymamalı (fallback: log).
"""

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

_GRAPH_URL = "https://graph.facebook.com/v19.0"


@dataclass
class InteractiveButton:
    """Hızlı yanıt butonu (max 3 adet, başlık max 20 karakter)."""
    id: str
    title: str


@dataclass
class ListRow:
    """Liste satırı (başlık max 24 karakter, açıklama max 72 karakter)."""
    id: str
    title: str
    description: str = ""


@dataclass
class ListSection:
    """Liste bölümü (başlık + satırlar)."""
    title: str
    rows: list[ListRow] = field(default_factory=list)


async def send_text(
    phone_number_id: str,
    access_token: str,
    to: str,
    text: str,
) -> bool:
    """
    Düz metin mesajı gönderir.

    to: alıcının WA numarası, "+" olmadan (örn: "905551234567")
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text, "preview_url": False},
    }
    return await _post(phone_number_id, access_token, payload)


async def send_buttons(
    phone_number_id: str,
    access_token: str,
    to: str,
    body: str,
    buttons: list[InteractiveButton],
    footer: str = "",
) -> bool:
    """
    Butonlu interaktif mesaj gönderir (maks 3 buton).

    body: mesaj metni
    footer: opsiyonel alt metin (gri, küçük font)
    """
    interactive: dict = {
        "type": "button",
        "body": {"text": body},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": btn.id, "title": btn.title}}
                for btn in buttons
            ]
        },
    }
    if footer:
        interactive["footer"] = {"text": footer}

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }
    return await _post(phone_number_id, access_token, payload)


async def send_list(
    phone_number_id: str,
    access_token: str,
    to: str,
    body: str,
    button_label: str,
    sections: list[ListSection],
    header: str = "",
    footer: str = "",
) -> bool:
    """
    Liste interaktif mesajı gönderir (maks 10 bölüm, toplam maks 10 satır).

    button_label: listeyi açan buton metni (max 20 karakter)
    sections: her bölümün başlığı ve satırları
    """
    interactive: dict = {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": button_label,
            "sections": [
                {
                    "title": sec.title,
                    "rows": [
                        {
                            "id": row.id,
                            "title": row.title[:24],
                            "description": row.description[:72],
                        }
                        for row in sec.rows
                    ],
                }
                for sec in sections
            ],
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": header}
    if footer:
        interactive["footer"] = {"text": footer}

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }
    return await _post(phone_number_id, access_token, payload)


async def send_template(
    phone_number_id: str,
    access_token: str,
    to: str,
    template_name: str,
    language_code: str,
    body_parameters: list[str],
) -> bool:
    """Onayli WhatsApp template mesaji gonderir."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": value}
                        for value in body_parameters
                    ],
                }
            ],
        },
    }
    return await _post(phone_number_id, access_token, payload)


async def _post(phone_number_id: str, access_token: str, payload: dict) -> bool:
    """Meta Graph API'ye POST atar; başarıda True, hatada False döner."""
    url = f"{_GRAPH_URL}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(
                "WA mesaj gönderilemedi | to=%s status=%s body=%s",
                payload.get("to"),
                response.status_code,
                response.text[:300],
            )
            return False
        return True
    except Exception as exc:
        logger.error("WA mesaj gönderme hatası | to=%s error=%s", payload.get("to"), exc)
        return False
