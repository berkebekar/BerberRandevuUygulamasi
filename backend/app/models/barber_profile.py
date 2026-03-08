"""
barber_profile.py — BarberProfile tablosu (CLAUDE.md).
Tenant başına 1 kayıt; slot süresi ve çalışma saatleri.
"""

import uuid
from sqlalchemy import DateTime, ForeignKey, Integer, String, Time, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BarberProfile(Base):
    """Berber çalışma ayarları; tenant_id unique."""

    __tablename__ = "barber_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        unique=True,
        nullable=False,
    )
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    work_start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    work_end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    weekly_closed_days: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, server_default=text("'{}'::integer[]")
    )
    max_booking_days_ahead: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("14")
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<BarberProfile id={self.id!r} tenant_id={self.tenant_id!r}>"
