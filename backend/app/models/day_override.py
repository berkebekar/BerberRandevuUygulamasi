"""
day_override.py — DayOverride tablosu (CLAUDE.md).
Belirli bir gün için kapalı veya özel çalışma saatleri.
"""

import uuid
from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, Integer, Time, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DayOverride(Base):
    """Günlük özel ayar; (tenant_id, date) unique."""

    __tablename__ = "day_overrides"
    __table_args__ = (UniqueConstraint("tenant_id", "date", name="uq_day_overrides_tenant_date"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    work_start_time: Mapped[Time | None] = mapped_column(Time, nullable=True)
    work_end_time: Mapped[Time | None] = mapped_column(Time, nullable=True)
    slot_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<DayOverride id={self.id!r} date={self.date!r}>"
