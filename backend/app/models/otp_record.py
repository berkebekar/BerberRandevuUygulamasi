"""
otp_record.py — OTPRecord tablosu (CLAUDE.md).
OTP kodu bcrypt hash; plain text asla saklanmaz.
"""

import uuid
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import OTPRole


class OTPRecord(Base):
    """OTP kaydı; code_hash bcrypt, role user veya admin."""

    __tablename__ = "otp_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[OTPRole] = mapped_column(
        Enum(OTPRole, name="otprole", create_constraint=True),
        nullable=False,
    )
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<OTPRecord id={self.id!r} phone={self.phone!r} role={self.role!r}>"
