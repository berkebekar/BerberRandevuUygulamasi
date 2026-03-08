"""
admin/service.py - Admin panel business logic.

Bu dosya admin paneli icin veri toplama islemlerini yapar.
HTTP katmani (router.py) buradan aldigi veriyi response'a cevirir.
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.booking import service as booking_service
from app.modules.schedule import service as schedule_service


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
