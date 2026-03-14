"""
uptime_check.py - Servis saglik kontrol kayitlari.
"""

import uuid

from sqlalchemy import DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UptimeCheck(Base):
    """Periyodik servis saglik kayitlari."""

    __tablename__ = "uptime_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    service_name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checked_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<UptimeCheck id={self.id!r} service_name={self.service_name!r} status={self.status!r}>"
