"""
enums.py — Veritabanı ENUM tipleri (CLAUDE.md).
Booking, OTPRecord ve NotificationLog tablolarında kullanılır.
"""

import enum


class BookingStatus(str, enum.Enum):
    """Randevu durumu: onaylı veya iptal."""
    confirmed = "confirmed"
    cancelled = "cancelled"
    no_show = "no_show"


class CancelledBy(str, enum.Enum):
    """Randevuyu iptal eden taraf."""
    admin = "admin"
    user = "user"


class OTPRole(str, enum.Enum):
    """OTP'nin hangi rol için üretildiği."""
    user = "user"
    admin = "admin"


class NotificationMessageType(str, enum.Enum):
    """Bildirim mesaj türü (MVP'de çoğunlukla otp)."""
    otp = "otp"
    booking_created = "booking_created"
    booking_cancelled = "booking_cancelled"


class NotificationStatus(str, enum.Enum):
    """Bildirim gönderim sonucu."""
    sent = "sent"
    failed = "failed"
    pending = "pending"
