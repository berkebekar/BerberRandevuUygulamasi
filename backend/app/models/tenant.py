"""
tenant.py — Tenant tablosu (CLAUDE.md).
Tek berber işletmesi; subdomain ile çözümlenir.
"""

import uuid
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import TenantStatus


class Tenant(Base):
    """Tek tenant (berber); subdomain benzersiz."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    parent_tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    subdomain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    whatsapp_waba_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    whatsapp_display_phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    whatsapp_connection_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="disconnected"
    )
    whatsapp_connected_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    whatsapp_bot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_bot_superadmin_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_booking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_booking_superadmin_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_reminder_superadmin_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_cancellation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_cancellation_superadmin_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_reschedule_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_reschedule_superadmin_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    whatsapp_silent_numbers: Mapped[list[str]] = mapped_column(JSON, nullable=False, server_default=text("'[]'"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenantstatus", create_constraint=True),
        nullable=False,
        server_default=TenantStatus.active.value,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id!r} subdomain={self.subdomain!r}>"
