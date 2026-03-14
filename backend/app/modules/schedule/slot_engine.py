"""
schedule/slot_engine.py - Slot hesaplama cekirdegi.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.barber_profile import BarberProfile
from app.models.day_override import DayOverride
from app.modules.schedule.schemas import DaySlots, SlotItem, SlotStatus

TZ = ZoneInfo("Europe/Istanbul")
DEFAULT_MAX_BOOKING_DAYS_AHEAD = 14


def to_utc(dt: datetime) -> datetime:
    """Herhangi bir datetime degerini UTC'ye cevirir."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def resolve_max_booking_days_ahead(profile: BarberProfile | None) -> int:
    """BarberProfile kaydindan ileri tarih limitini cozer."""
    if profile is None:
        return DEFAULT_MAX_BOOKING_DAYS_AHEAD
    raw_value = getattr(profile, "max_booking_days_ahead", DEFAULT_MAX_BOOKING_DAYS_AHEAD)
    if isinstance(raw_value, int) and raw_value > 0:
        return raw_value
    return DEFAULT_MAX_BOOKING_DAYS_AHEAD


def resolve_slot_duration_minutes(profile: BarberProfile, override: DayOverride | None) -> int:
    """Gunluk slot suresini cozer."""
    if override is not None:
        raw_value = getattr(override, "slot_duration_minutes", None)
        if isinstance(raw_value, int) and raw_value > 0:
            return raw_value
    return profile.slot_duration_minutes


def resolve_day_end_datetime(target_date: date, end_time: time) -> datetime:
    """00:00 bitis saatini gun sonu (24:00) olarak yorumlar."""
    if end_time == time(0, 0):
        return datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=TZ)
    return datetime.combine(target_date, end_time, tzinfo=TZ)


def build_day_slots(
    profile: BarberProfile,
    override: DayOverride | None,
    bookings: list,
    blocks: list,
    target_date: date,
    now: datetime,
) -> DaySlots:
    """Tek bir gun icin slot listesini hesaplar."""
    weekday = target_date.weekday()
    max_booking_days_ahead = resolve_max_booking_days_ahead(profile)
    if profile.weekly_closed_days and weekday in profile.weekly_closed_days:
        return DaySlots(
            date=target_date,
            is_closed=True,
            max_booking_days_ahead=max_booking_days_ahead,
            slots=[],
        )

    if override and override.is_closed:
        return DaySlots(
            date=target_date,
            is_closed=True,
            max_booking_days_ahead=max_booking_days_ahead,
            slots=[],
        )

    start_time = (
        override.work_start_time if override and override.work_start_time else profile.work_start_time
    )
    end_time = override.work_end_time if override and override.work_end_time else profile.work_end_time
    duration = timedelta(minutes=resolve_slot_duration_minutes(profile, override))

    slot_datetimes: list[datetime] = []
    current = datetime.combine(target_date, start_time, tzinfo=TZ)
    day_end = resolve_day_end_datetime(target_date, end_time)

    while current + duration <= day_end:
        slot_datetimes.append(current)
        current += duration

    booked_utc: set[datetime] = {to_utc(b.slot_time) for b in bookings}
    blocked_utc: set[datetime] = {to_utc(b.blocked_at) for b in blocks}

    slots: list[SlotItem] = []
    for slot_dt in slot_datetimes:
        slot_utc = to_utc(slot_dt)

        if slot_dt <= now:
            status = SlotStatus.past
        elif slot_utc in booked_utc:
            status = SlotStatus.booked
        elif slot_utc in blocked_utc:
            status = SlotStatus.blocked
        else:
            status = SlotStatus.available

        slots.append(
            SlotItem(
                time=slot_dt.strftime("%H:%M"),
                datetime=slot_dt,
                end_datetime=slot_dt + duration,
                status=status,
            )
        )

    return DaySlots(
        date=target_date,
        is_closed=False,
        max_booking_days_ahead=max_booking_days_ahead,
        slots=slots,
    )
