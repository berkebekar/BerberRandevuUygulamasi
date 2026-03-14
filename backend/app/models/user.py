"""
user.py — User tablosu (CLAUDE.md).
Müşteri; tenant_id + phone unique.
"""

import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, String, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Müşteri; (tenant_id, phone) birlikte unique."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),)

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
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    session_version: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        server_default=text("gen_random_uuid()::text"),
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} phone={self.phone!r}>"
