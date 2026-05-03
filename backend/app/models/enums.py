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
    """Randevuyu iptal eden veya degistiren taraf."""
    admin = "admin"
    user = "user"
    rescheduled_by_user = "rescheduled_by_user"
    rescheduled_by_admin = "rescheduled_by_admin"


class OTPRole(str, enum.Enum):
    """OTP'nin hangi rol için üretildiği."""
    user = "user"
    admin = "admin"


class TenantStatus(str, enum.Enum):
    """Tenant status: active, inactive, deleted."""
    active = "active"
    inactive = "inactive"
    deleted = "deleted"


class UserStatus(str, enum.Enum):
    """User status: active, blocked, deleted."""
    active = "active"
    blocked = "blocked"
    deleted = "deleted"
