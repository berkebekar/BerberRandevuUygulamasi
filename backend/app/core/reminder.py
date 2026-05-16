"""
reminder.py — Randevuya 90 dakika kala WP hatirlatmasi.
Her 2 dakikada bir slot_time'a 88-92 dakika kalan confirmed randevulari kontrol eder;
reminder_sent=False olanlara mesaj gonderir ve flag'i true yapar.
"""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.phone import normalize_tr_phone
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.whatsapp import client as wa_client
from app.modules.whatsapp.tenant_config import get_tenant_whatsapp_credentials

logger = logging.getLogger(__name__)

_TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


def _tr_datetime(dt: datetime) -> str:
    local = dt.astimezone(ZoneInfo("Europe/Istanbul"))
    return f"{local.day} {_TR_MONTHS[local.month - 1]} {local.strftime('%H:%M')}"


def _full_name(tenant: Tenant) -> str:
    fn = (tenant.first_name or "").strip()
    ln = (tenant.last_name or "").strip()
    if fn and ln:
        return f"{fn} {ln}"
    return (fn or ln or tenant.name).strip()


async def send_reminders() -> None:
    """88-92 dakika icinde randevusu olan, henuz hatirlatilmamis musterilere WP gonderir."""
    settings = get_settings()
    if not settings.wa_access_token:
        return

    now = datetime.now(tz=ZoneInfo("Europe/Istanbul"))
    window_start = now + timedelta(minutes=88)
    window_end = now + timedelta(minutes=92)

    async with AsyncSessionLocal() as db:
        b_res = await db.execute(
            select(Booking).where(
                Booking.status == BookingStatus.confirmed,
                Booking.reminder_sent.is_(False),
                Booking.slot_time >= window_start,
                Booking.slot_time < window_end,
            )
        )
        bookings = b_res.scalars().all()

        if not bookings:
            return

        # Oncelikle flag'leri set et; WP hatasi olsa bile tekrar mesaj gitmez.
        for b in bookings:
            b.reminder_sent = True
        await db.commit()

        for booking in bookings:
            try:
                t_res = await db.execute(select(Tenant).where(Tenant.id == booking.tenant_id))
                tenant = t_res.scalar_one_or_none()
                if not tenant:
                    continue
                creds = await get_tenant_whatsapp_credentials(db, tenant.id)
                if creds is None:
                    continue

                u_res = await db.execute(select(User).where(User.id == booking.user_id))
                user = u_res.scalar_one_or_none()
                if not user:
                    continue

                try:
                    wa_phone = normalize_tr_phone(user.phone).lstrip("+")
                except Exception:
                    wa_phone = user.phone.lstrip("+")

                slot_str = _tr_datetime(booking.slot_time)
                barber = _full_name(tenant)
                msg = (
                    f"Merhaba {user.first_name}! "
                    f"{slot_str} tarihindeki {barber} randevunuz yaklaşıyor. "
                    f"Sizi bekliyoruz! ✂️"
                )
                await wa_client.send_text(
                    creds.phone_number_id,
                    creds.access_token,
                    wa_phone,
                    msg,
                )
            except Exception:
                logger.exception("Reminder WP send failed for booking %s", booking.id)
