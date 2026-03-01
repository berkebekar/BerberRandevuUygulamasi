"""
booking/schemas.py - Booking modulu Pydantic semalari.

Bu dosya HTTP katmanindaki request/response modellerini tanimlar.
Semalar sadece veri dogrulama yapar; is kurallari service.py'dedir.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models.enums import BookingStatus, CancelledBy


class BookingCreateRequest(BaseModel):
    """Musteri randevu olusturma istegi."""

    slot_time: datetime

    @field_validator("slot_time")
    @classmethod
    def slot_time_must_be_timezone_aware(cls, v: datetime) -> datetime:
        """Randevu zamani timezone bilgisi icermelidir (ornek: +03:00)."""
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("slot_time timezone bilgisi icermelidir")
        return v


class AdminBookingCreateRequest(BaseModel):
    """Admin manuel randevu olusturma istegi."""

    slot_time: datetime
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    @field_validator("slot_time")
    @classmethod
    def slot_time_must_be_timezone_aware(cls, v: datetime) -> datetime:
        """Randevu zamani timezone bilgisi icermelidir (ornek: +03:00)."""
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("slot_time timezone bilgisi icermelidir")
        return v


class BookingResponse(BaseModel):
    """Tek randevu yaniti."""

    id: uuid.UUID
    user_id: uuid.UUID
    slot_time: datetime
    status: BookingStatus
    cancelled_by: CancelledBy | None
    created_at: datetime


class BookingWithUserResponse(BaseModel):
    """Admin gorunumu icin randevu + musteri bilgileri."""

    id: uuid.UUID
    user_id: uuid.UUID
    user_first_name: str
    user_last_name: str
    user_phone: str
    slot_time: datetime
    status: BookingStatus
    cancelled_by: CancelledBy | None
    created_at: datetime
