"""
admin/schemas.py - Admin panel request/response Pydantic semalari.

Bu dosya admin endpoint'lerinin veri modellerini tanimlar.
Business logic yoktur; sadece veri dogrulama ve serilestirme yapilir.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import BookingStatus, CancelledBy
from app.modules.schedule.schemas import SlotStatus


class DashboardBookingItem(BaseModel):
    """
    Dashboard'da gosterilen tek randevu satiri.
    Her randevuya musterinin adi, soyadi ve telefonu dahildir.
    """
    id: uuid.UUID
    user_first_name: str
    user_last_name: str
    user_phone: str
    slot_time: datetime
    status: BookingStatus
    cancelled_by: CancelledBy | None


class DashboardResponse(BaseModel):
    """
    Admin dashboard yaniti.

    Alanlar:
    - date: Sorgulanan gun (YYYY-MM-DD)
    - bookings: O gunun tum randevulari (confirmed + cancelled), slot_time ASC sirali
    """
    date: date
    bookings: list[DashboardBookingItem]


class OverviewSlotItem(BaseModel):
    """
    Admin overview icinde donen tek bir slot kaydi.
    'time' alani UI'da hizli gosterim icin korunur.
    """
    time: str
    datetime: datetime
    end_datetime: datetime
    status: SlotStatus


class OverviewBlockedSlotItem(BaseModel):
    """
    Admin overview icinde donen tek blok kaydi.
    block_id, slot acma islemi icin UI'da gereklidir.
    """
    id: uuid.UUID
    blocked_at: datetime
    reason: str | None


class AdminOverviewResponse(BaseModel):
    """
    Admin paneli icin birlesik yanit.

    Tek cagrida dashboard + slotlar + bloklar doner.
    Boylece ayri ayri polling cagrilari azaltilir.
    """
    date: date
    bookings: list[DashboardBookingItem]
    is_closed: bool
    slots: list[OverviewSlotItem]
    blocks: list[OverviewBlockedSlotItem]
