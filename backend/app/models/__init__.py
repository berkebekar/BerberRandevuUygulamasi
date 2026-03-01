"""
models — SQLAlchemy ORM modelleri (CLAUDE.md).
Tüm modeller buradan export edilir; Alembic metadata için hepsi import edilmiş olmalı.
"""

from app.models.base import Base
from app.models.tenant import Tenant
from app.models.admin import Admin
from app.models.user import User
from app.models.barber_profile import BarberProfile
from app.models.day_override import DayOverride
from app.models.slot_block import SlotBlock
from app.models.booking import Booking
from app.models.otp_record import OTPRecord
from app.models.notification_log import NotificationLog

__all__ = [
    "Base",
    "Tenant",
    "Admin",
    "User",
    "BarberProfile",
    "DayOverride",
    "SlotBlock",
    "Booking",
    "OTPRecord",
    "NotificationLog",
]
