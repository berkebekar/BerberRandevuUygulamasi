"""
admin/service.py - Admin panel business logic.

Bu dosya admin paneli icin veri toplama islemlerini yapar.
HTTP katmani (router.py) buradan aldigi veriyi response'a cevirir.
"""

import uuid
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.user import User
from app.modules.booking import service as booking_service
from app.modules.schedule import service as schedule_service

TZ = ZoneInfo("Europe/Istanbul")


def _to_local_tz(dt: datetime) -> datetime:
    """Datetime degerini guvenli sekilde Istanbul timezone'una cevirir."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(TZ)
    return dt.astimezone(TZ)


def _serialize_dashboard_rows(rows: list[tuple]) -> list[dict]:
    """
    Booking + User satirlarini dashboard item listesine cevirir.
    Bu donusum tek yerde tutulur; dashboard ve overview ayni veriyi kullanir.
    """
    return [
        {
            "id": booking.id,
            "user_first_name": user.first_name,
            "user_last_name": user.last_name,
            "user_phone": user.phone,
            "slot_time": booking.slot_time,
            "status": booking.status,
            "cancelled_by": booking.cancelled_by,
        }
        for booking, user in rows
    ]


async def get_dashboard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> dict:
    """
    Belirli bir gun icin admin dashboard verisini hazirlar.
    """
    rows = await booking_service.get_bookings_by_date(db, tenant_id, target_date)

    return {
        "date": target_date,
        "bookings": _serialize_dashboard_rows(rows),
    }


async def get_overview(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> dict:
    """
    Admin paneli icin birlesik veri dondurur.

    Tek cagrida dashboard + gunluk slotlar + bloklu slotlar birlesir.
    Bu yapi, frontend'in ayri ayri polling cagrilarini azaltir.
    """
    # Dashboard listesi icin booking + user satirlarini cek.
    booking_rows = await booking_service.get_bookings_by_date(db, tenant_id, target_date)

    # Gunluk slot listesini cek.
    day_slots = await schedule_service.get_slots_for_date(db, tenant_id, target_date)

    # Slot acma islemi icin block_id'ler gerekir.
    blocks = await schedule_service.get_blocks_for_date(db, tenant_id, target_date)

    return {
        "date": target_date,
        "bookings": _serialize_dashboard_rows(booking_rows),
        "is_closed": day_slots.is_closed,
        "max_booking_days_ahead": getattr(day_slots, "max_booking_days_ahead", 14),
        "slots": [
            {
                "time": slot.time,
                "datetime": slot.datetime,
                "end_datetime": slot.end_datetime,
                "status": slot.status,
            }
            for slot in day_slots.slots
        ],
        "blocks": [
            {
                "id": block.id,
                "blocked_at": block.blocked_at,
                "reason": block.reason,
            }
            for block in blocks
        ],
    }


def _round_rate(numerator: int, denominator: int) -> float:
    """Oranlari 0-100 araliginda tek ondalikli olarak dondurur."""
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _range_start_end(target_date: date, kind: str) -> tuple[date, date]:
    """Secili tarihe gore gunluk, haftalik veya aylik takvim araligini cozer."""
    if kind == "daily":
        return target_date, target_date
    if kind == "weekly":
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)
        return start_date, end_date
    if kind == "monthly":
        start_date = target_date.replace(day=1)
        if target_date.month == 12:
            next_month = date(target_date.year + 1, 1, 1)
        else:
            next_month = date(target_date.year, target_date.month + 1, 1)
        return start_date, next_month - timedelta(days=1)
    raise ValueError(f"Unsupported statistics period: {kind}")


async def _get_booking_rows_in_range(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[tuple[Booking, User]]:
    """Belirli tarih araligindaki booking + user satirlarini dondurur."""
    start_dt = datetime.combine(start_date, time.min, tzinfo=TZ)
    end_dt = datetime.combine(end_date, time.max, tzinfo=TZ)
    result = await db.execute(
        select(Booking, User)
        .join(User, User.id == Booking.user_id)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.slot_time >= start_dt,
            Booking.slot_time <= end_dt,
        )
        .order_by(Booking.slot_time.asc())
    )
    return list(result.all())


async def _get_first_booking_map(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_ids: list[uuid.UUID],
) -> dict[uuid.UUID, datetime]:
    """Verilen kullanicilar icin ilk booking zamanini dondurur."""
    if not user_ids:
        return {}
    result = await db.execute(
        select(Booking.user_id, func.min(Booking.slot_time))
        .where(
            Booking.tenant_id == tenant_id,
            Booking.user_id.in_(user_ids),
        )
        .group_by(Booking.user_id)
    )
    return {
        user_id: first_slot
        for user_id, first_slot in result.all()
        if user_id is not None and first_slot is not None
    }


def _build_summary(rows: list[tuple[Booking, User]], now: datetime) -> dict:
    """Booking satirlarindan donem ozetini hesaplar."""
    total_bookings = len(rows)
    completed_count = 0
    no_show_count = 0
    cancelled_count = 0

    for booking, _user in rows:
        if booking.status.value == "cancelled":
            cancelled_count += 1
            continue
        if booking.status.value == "no_show":
            no_show_count += 1
            continue
        if _to_local_tz(booking.slot_time) <= now:
            completed_count += 1

    return {
        "total_bookings": total_bookings,
        "completed_count": completed_count,
        "no_show_count": no_show_count,
        "cancelled_count": cancelled_count,
        "completion_rate": _round_rate(completed_count, total_bookings),
        "no_show_rate": _round_rate(no_show_count, total_bookings),
        "cancellation_rate": _round_rate(cancelled_count, total_bookings),
    }


async def _build_customer_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
    rows: list[tuple[Booking, User]],
) -> dict:
    """Yeni ve tekrar gelen musteri sayilarini hesaplar."""
    unique_user_ids = list({booking.user_id for booking, _user in rows})
    first_booking_map = await _get_first_booking_map(db, tenant_id, unique_user_ids)
    start_dt = datetime.combine(start_date, time.min, tzinfo=TZ)
    end_dt = datetime.combine(end_date, time.max, tzinfo=TZ)

    new_customers = 0
    returning_customers = 0
    for user_id in unique_user_ids:
        first_booking = first_booking_map.get(user_id)
        if first_booking is None:
            continue
        if start_dt <= _to_local_tz(first_booking) <= end_dt:
            new_customers += 1
        else:
            returning_customers += 1

    return {
        "start_date": start_date,
        "end_date": end_date,
        "new_customers": new_customers,
        "returning_customers": returning_customers,
    }


async def _build_capacity_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
    rows: list[tuple[Booking, User]],
    now: datetime,
) -> dict:
    """Doluluk ve en yogun gun/saat metriklerini hesaplar."""
    total_capacity_slots = 0
    for offset in range((end_date - start_date).days + 1):
        current_date = start_date + timedelta(days=offset)
        day_slots = await schedule_service.get_slots_for_date(db, tenant_id, current_date, now=now)
        total_capacity_slots += len(day_slots.slots)

    occupied_slot_keys = {
        _to_local_tz(booking.slot_time).isoformat()
        for booking, _user in rows
        if booking.status.value != "cancelled"
    }
    occupied_slots = len(occupied_slot_keys)

    day_counter = Counter()
    hour_counter = Counter()
    for booking, _user in rows:
        if booking.status.value == "cancelled":
            continue
        slot_local = _to_local_tz(booking.slot_time)
        day_counter[slot_local.date()] += 1
        hour_counter[slot_local.strftime("%H:%M")] += 1

    busiest_day = {"label": None, "value": 0}
    if day_counter:
        top_day = min(
            (day for day, count in day_counter.items() if count == max(day_counter.values())),
            key=lambda item: item,
        )
        busiest_day = {
            "label": top_day.isoformat(),
            "value": day_counter[top_day],
        }

    busiest_hour = {"label": None, "value": 0}
    if hour_counter:
        max_hour_value = max(hour_counter.values())
        top_hour = min(
            (hour for hour, count in hour_counter.items() if count == max_hour_value),
            key=lambda item: item,
        )
        busiest_hour = {
            "label": top_hour,
            "value": hour_counter[top_hour],
        }

    return {
        "start_date": start_date,
        "end_date": end_date,
        "occupancy_rate": _round_rate(occupied_slots, total_capacity_slots),
        "total_capacity_slots": total_capacity_slots,
        "occupied_slots": occupied_slots,
        "busiest_day": busiest_day,
        "busiest_hour": busiest_hour,
    }


async def _build_period_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
    kind: str,
    now: datetime,
) -> tuple[dict, dict, dict]:
    """Tek donem icin summary, customer ve capacity metriklerini birlikte hesaplar."""
    start_date, end_date = _range_start_end(target_date, kind)
    rows = await _get_booking_rows_in_range(db, tenant_id, start_date, end_date)

    summary = {
        "start_date": start_date,
        "end_date": end_date,
        **_build_summary(rows, now),
    }
    customer_stats = await _build_customer_stats(db, tenant_id, start_date, end_date, rows)
    capacity_stats = await _build_capacity_stats(db, tenant_id, start_date, end_date, rows, now)
    return summary, customer_stats, capacity_stats


async def get_statistics(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> dict:
    """Admin istatistik ekrani icin tum donem verilerini toplar."""
    now = datetime.now(TZ)
    daily_summary, daily_customer, daily_capacity = await _build_period_stats(
        db, tenant_id, target_date, "daily", now
    )
    weekly_summary, weekly_customer, weekly_capacity = await _build_period_stats(
        db, tenant_id, target_date, "weekly", now
    )
    monthly_summary, monthly_customer, monthly_capacity = await _build_period_stats(
        db, tenant_id, target_date, "monthly", now
    )

    return {
        "selected_date": target_date,
        "daily_summary": daily_summary,
        "weekly_summary": weekly_summary,
        "monthly_summary": monthly_summary,
        "customer_stats": {
            "daily": daily_customer,
            "weekly": weekly_customer,
            "monthly": monthly_customer,
        },
        "capacity_stats": {
            "daily": daily_capacity,
            "weekly": weekly_capacity,
            "monthly": monthly_capacity,
        },
    }
