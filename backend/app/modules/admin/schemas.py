"""
admin/schemas.py — Admin panel request/response Pydantic şemaları.

Bu dosya admin dashboard endpoint'inin veri modellerini tanımlar.
Business logic yoktur; sadece veri doğrulama ve serileştirme yapılır.
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.enums import BookingStatus, CancelledBy


# ─── Dashboard Response Şemaları ──────────────────────────────────────────────

class DashboardBookingItem(BaseModel):
    """
    Dashboard'da gösterilen tek randevu satırı.
    Her randevuya müşterinin adı, soyadı ve telefonu dahildir —
    admin kimin geldiğini anında görebilsin.
    Para bilgisi yoktur (CLAUDE.md: ödeme MVP dışı).
    """
    id: uuid.UUID
    user_first_name: str
    user_last_name: str
    user_phone: str
    slot_time: datetime          # TR timezone (Europe/Istanbul)
    status: BookingStatus        # confirmed | cancelled | no_show
    cancelled_by: CancelledBy | None  # Sadece iptal edilmiş randevularda dolu


class DashboardResponse(BaseModel):
    """
    Admin dashboard yanıtı.

    Alanlar:
    - date: Sorgulanan gün (YYYY-MM-DD)
    - bookings: O günün tüm randevuları (confirmed + cancelled), slot_time ASC sıralı
    """
    date: date
    bookings: list[DashboardBookingItem]
