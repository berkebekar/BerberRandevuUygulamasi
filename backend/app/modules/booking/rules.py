"""
booking/rules.py - Booking domain helper'lari.
"""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BOOKING_MAX_DAYS_AHEAD
from app.models.barber_profile import BarberProfile
from app.models.day_override import DayOverride

TZ = ZoneInfo("Europe/Istanbul")


def to_local_tz(dt: datetime) -> datetime:
    """DB datetime degerini guvenli sekilde Istanbul timezone'una cevirir."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(TZ)
    return dt.astimezone(TZ)


def resolve_max_days_ahead(profile: BarberProfile | None) -> int:
    """Ileri tarih limitini profile kaydindan cozer, yoksa varsayilana doner."""
    if profile is None:
        return BOOKING_MAX_DAYS_AHEAD
    value = getattr(profile, "max_booking_days_ahead", BOOKING_MAX_DAYS_AHEAD)
    if isinstance(value, int) and value > 0:
        return value
    return BOOKING_MAX_DAYS_AHEAD


def resolve_day_end_datetime(target_date: date, end_time: time) -> datetime:
    """00:00 bitisi gun sonu (24:00) kabul edilir."""
    if end_time == time(0, 0):
        return datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=TZ)
    return datetime.combine(target_date, end_time, tzinfo=TZ)


async def validate_slot_in_schedule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    slot_local: datetime,
    profile: BarberProfile | None = None,
) -> bool:
    """
    Verilen slotun takvimde var olup olmadigini kontrol eder.
    Booking/block durumunu kontrol etmez.
    """
    if profile is None:
        profile_result = await db.execute(
            select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
        )
        profile = profile_result.scalar_one_or_none()
    if profile is None:
        return False

    weekly_closed_days = getattr(profile, "weekly_closed_days", []) or []
    if slot_local.weekday() in weekly_closed_days:
        return False

    override_result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date == slot_local.date(),
        )
    )
    override = override_result.scalar_one_or_none()
    if override and override.is_closed:
        return False

    start_time = (
        override.work_start_time if override and override.work_start_time else profile.work_start_time
    )
    end_time = override.work_end_time if override and override.work_end_time else profile.work_end_time
    override_duration = getattr(override, "slot_duration_minutes", None) if override else None
    duration_minutes = (
        override_duration
        if isinstance(override_duration, int) and override_duration > 0
        else profile.slot_duration_minutes
    )
    duration = timedelta(minutes=duration_minutes)

    day_start = datetime.combine(slot_local.date(), start_time, tzinfo=TZ)
    day_end = resolve_day_end_datetime(slot_local.date(), end_time)

    if slot_local < day_start or slot_local >= day_end:
        return False
    if slot_local + duration > day_end:
        return False

    elapsed_seconds = int((slot_local - day_start).total_seconds())
    duration_seconds = int(duration.total_seconds())
    if elapsed_seconds % duration_seconds != 0:
        return False
    return True
