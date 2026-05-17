"""Long absence WhatsApp template reminders."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.orm import aliased

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.phone import normalize_tr_phone
from app.models.booking import Booking
from app.models.enums import BookingStatus, TenantStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.models.wa_long_absence_reminder import WaLongAbsenceReminder
from app.modules.whatsapp import client as wa_client
from app.modules.whatsapp.settings import build_whatsapp_feature_settings, is_silent_contact
from app.modules.whatsapp.tenant_config import get_tenant_whatsapp_credentials

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Istanbul")


def _display_business_name(tenant: Tenant) -> str:
    first_name = (tenant.first_name or "").strip()
    last_name = (tenant.last_name or "").strip()
    full_name = f"{first_name} {last_name}".strip()
    return full_name or tenant.name.strip()


def _wa_phone(phone: str) -> str:
    try:
        return normalize_tr_phone(phone).lstrip("+")
    except Exception:
        return phone.lstrip("+")


async def send_long_absence_reminders() -> None:
    """Send one approved template after the configured inactivity window."""
    settings = get_settings()
    if not settings.wa_access_token:
        return

    now = datetime.now(tz=TZ)

    async with AsyncSessionLocal() as db:
        tenant_result = await db.execute(
            select(Tenant).where(
                Tenant.status == TenantStatus.active,
                Tenant.is_active.is_(True),
                Tenant.whatsapp_connection_status == "connected",
                Tenant.whatsapp_phone_number_id.is_not(None),
            )
        )
        tenants = list(tenant_result.scalars().all())

        for tenant in tenants:
            features = build_whatsapp_feature_settings(tenant)
            if not features.long_absence_effective_enabled:
                continue
            creds = await get_tenant_whatsapp_credentials(db, tenant.id)
            if creds is None:
                continue

            cutoff = now - timedelta(days=features.long_absence_days)
            last_completed = (
                select(
                    Booking.user_id.label("user_id"),
                    func.max(Booking.slot_time).label("last_slot_time"),
                )
                .where(
                    Booking.tenant_id == tenant.id,
                    Booking.status == BookingStatus.confirmed,
                    Booking.slot_time <= now,
                )
                .group_by(Booking.user_id)
                .subquery()
            )
            future_booking = aliased(Booking)
            has_future_booking = exists().where(
                future_booking.tenant_id == tenant.id,
                future_booking.user_id == User.id,
                future_booking.status == BookingStatus.confirmed,
                future_booking.slot_time > now,
            )
            already_sent_for_booking = exists().where(
                WaLongAbsenceReminder.tenant_id == tenant.id,
                WaLongAbsenceReminder.booking_id == Booking.id,
            )

            rows_result = await db.execute(
                select(Booking, User)
                .join(
                    last_completed,
                    (last_completed.c.user_id == Booking.user_id)
                    & (last_completed.c.last_slot_time == Booking.slot_time),
                )
                .join(User, User.id == Booking.user_id)
                .where(
                    Booking.tenant_id == tenant.id,
                    Booking.status == BookingStatus.confirmed,
                    Booking.slot_time <= cutoff,
                    User.is_blocked.is_(False),
                    ~has_future_booking,
                    ~already_sent_for_booking,
                )
                .order_by(Booking.slot_time.asc())
                .limit(100)
            )
            rows = list(rows_result.all())
            if not rows:
                continue

            business_name = _display_business_name(tenant)
            for booking, user in rows:
                wa_phone = _wa_phone(user.phone)
                if is_silent_contact(tenant, wa_phone):
                    continue

                ok = await wa_client.send_template(
                    creds.phone_number_id,
                    creds.access_token,
                    wa_phone,
                    settings.wa_long_absence_template_name,
                    settings.wa_long_absence_template_language,
                    [user.first_name, business_name],
                )
                if not ok:
                    continue

                db.add(
                    WaLongAbsenceReminder(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        booking_id=booking.id,
                    )
                )
                try:
                    await db.commit()
                except Exception:
                    await db.rollback()
                    logger.exception("Long absence reminder ledger write failed for booking %s", booking.id)
