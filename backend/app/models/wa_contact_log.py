"""wa_contact_log.py — WhatsApp bot benzersiz kullanıcı takibi."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WaContactLog(Base):
    """Her (tenant, wa_phone, tarih) kombinasyonu için en fazla bir kayıt tutar."""

    __tablename__ = "wa_contact_logs"

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
    wa_phone: Mapped[str] = mapped_column(Text, nullable=False)
    contact_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "wa_phone", "contact_date",
            name="uq_wa_contact_logs_tenant_phone_date",
        ),
    )
