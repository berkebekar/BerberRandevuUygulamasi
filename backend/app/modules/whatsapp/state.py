"""
whatsapp/state.py — Redis üzerinde konuşma state yönetimi.

Her kullanıcı (WA telefon numarası) için aktif konuşma adımı ve seçimler
Redis'te JSON olarak saklanır. 30 dakika hareketsizlik sonrası otomatik silinir.

State anahtarı: "wa_state:{phone_number_id}:{wa_phone}"
Bu yapı sayesinde farklı tenant'ların kullanıcıları birbirinden izole kalır.
"""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

STATE_TTL = 60 * 60 * 24 * 7  # 7 gün (saniye) — tenant seçiminin kaybolmaması için

# Konuşma adımları
STEP_IDLE = "idle"               # Ana menü bekleniyor
STEP_NAME_COLLECT = "name_collect" # Yeni kullanıcı: isim/soyisim bekleniyor
STEP_DATE_SELECT = "date_select" # Tarih seçimi
STEP_TIME_SELECT = "time_select" # Saat seçimi
STEP_CONFIRM = "confirm"         # Randevu onayı


@dataclass
class ConversationState:
    """Bir kullanıcının aktif konuşma durumu."""
    step: str = STEP_IDLE
    tenant_id: Optional[str] = None       # Hangi tenant
    wa_name: Optional[str] = None         # WhatsApp profil adı
    selected_date: Optional[str] = None   # "YYYY-MM-DD"
    selected_time: Optional[str] = None   # "HH:MM"
    user_id: Optional[str] = None         # DB'deki User.id (kaydedilmişse)
    slot_offset: int = 0                  # Saat listesi sayfalama: mevcut başlangıç indeksi


def _key(phone_number_id: str, wa_phone: str) -> str:
    return f"wa_state:{phone_number_id}:{wa_phone}"


async def get_state(phone_number_id: str, wa_phone: str) -> ConversationState:
    """
    Kullanıcının mevcut state'ini okur.
    Redis'te kayıt yoksa (yeni konuşma / süresi dolmuş) boş state döner.
    """
    redis = await get_redis()
    raw = await redis.get(_key(phone_number_id, wa_phone))
    if raw is None:
        return ConversationState()
    try:
        data = json.loads(raw)
        return ConversationState(**{k: v for k, v in data.items() if k in ConversationState.__dataclass_fields__})
    except Exception as exc:
        logger.warning("State parse hatası | phone=%s error=%s", wa_phone, exc)
        return ConversationState()


async def save_state(phone_number_id: str, wa_phone: str, state: ConversationState) -> None:
    """State'i kaydeder ve TTL'yi sıfırlar (her mesajda 30 dk uzar)."""
    redis = await get_redis()
    await redis.setex(
        _key(phone_number_id, wa_phone),
        STATE_TTL,
        json.dumps(asdict(state), ensure_ascii=False),
    )


async def clear_state(phone_number_id: str, wa_phone: str) -> None:
    """Konuşmayı sıfırlar (randevu tamamlandı, iptal edildi vb.)."""
    redis = await get_redis()
    await redis.delete(_key(phone_number_id, wa_phone))
