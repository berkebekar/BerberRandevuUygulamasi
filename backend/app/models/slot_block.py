"""
slot_block.py — SlotBlock tablosu (CLAUDE.md).
Bloke edilmiş slot; (tenant_id, blocked_at) unique.
"""

import uuid
from sqlalchemy import DateTime, ForeignKey, String, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SlotBlock(Base):
    """Bloke slot; (tenant_id, blocked_at) unique."""

    __tablename__ = "slot_blocks"
    __table_args__ = (UniqueConstraint("tenant_id", "blocked_at", name="uq_slot_blocks_tenant_blocked_at"),)

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
    blocked_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<SlotBlock id={self.id!r} blocked_at={self.blocked_at!r}>"
