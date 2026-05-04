"""wa_error_log.py — WhatsApp bot hata kayıtları."""

import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WaErrorLog(Base):
    """WhatsApp bot katmanında oluşan hatalar (genel error_logs'dan bağımsız)."""

    __tablename__ = "wa_error_logs"

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
    wa_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:
        return f"<WaErrorLog id={self.id!r} error_type={self.error_type!r}>"
