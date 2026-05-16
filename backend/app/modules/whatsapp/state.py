"""
whatsapp/state.py - Redis conversation state management.

State key: "wa_state:{phone_number_id}:{wa_phone}".
The Redis record is kept for 7 days. Short-lived rules such as the
15-minute booking flow and 3-hour human handoff are controlled by timestamp
fields inside the state.
"""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

STATE_TTL = 60 * 60 * 24 * 7

STEP_IDLE = "idle"
STEP_NAME_COLLECT = "name_collect"
STEP_DATE_SELECT = "date_select"
STEP_TIME_SELECT = "time_select"
STEP_CONFIRM = "confirm"
STEP_SAME_DAY_CONFIRM = "same_day_confirm"


@dataclass
class ConversationState:
    step: str = STEP_IDLE
    tenant_id: Optional[str] = None
    wa_name: Optional[str] = None
    selected_date: Optional[str] = None
    selected_time: Optional[str] = None
    user_id: Optional[str] = None
    slot_offset: int = 0
    mode: str = "idle"
    flow_expires_at: Optional[str] = None
    human_handoff_until: Optional[str] = None
    last_menu_sent_at: Optional[str] = None


def _key(phone_number_id: str, wa_phone: str) -> str:
    return f"wa_state:{phone_number_id}:{wa_phone}"


async def get_state(phone_number_id: str, wa_phone: str) -> ConversationState:
    redis = await get_redis()
    raw = await redis.get(_key(phone_number_id, wa_phone))
    if raw is None:
        return ConversationState()
    try:
        data = json.loads(raw)
        allowed = ConversationState.__dataclass_fields__
        return ConversationState(**{k: v for k, v in data.items() if k in allowed})
    except Exception as exc:
        logger.warning("WA state parse failed | phone=%s error=%s", wa_phone, exc)
        return ConversationState()


async def save_state(phone_number_id: str, wa_phone: str, state: ConversationState) -> None:
    redis = await get_redis()
    await redis.setex(
        _key(phone_number_id, wa_phone),
        STATE_TTL,
        json.dumps(asdict(state), ensure_ascii=False),
    )


async def clear_state(phone_number_id: str, wa_phone: str) -> None:
    redis = await get_redis()
    await redis.delete(_key(phone_number_id, wa_phone))
