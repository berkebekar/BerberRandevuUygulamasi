"""
booking.py — Booking tablosu (CLAUDE.md).
Partial unique: (tenant_id, slot_time) ve (tenant_id, user_id, date) WHERE status='confirmed'.
"""

import uuid
from sqlalchemy import DateTime, Enum, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import BookingStatus, CancelledBy


class Booking(Base):
    """Randevu; partial unique index'ler migration'da tanımlanacak."""

    __tablename__ = "bookings"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    slot_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="bookingstatus", create_constraint=True),
        nullable=False,
    )
    cancelled_by: Mapped[CancelledBy | None] = mapped_column(
        Enum(CancelledBy, name="cancelledby", create_constraint=True),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )

    def __repr__(self) -> str:
        return f"<Booking id={self.id!r} slot_time={self.slot_time!r} status={self.status!r}>"
