"""
notification_log.py — NotificationLog tablosu (CLAUDE.md).
SMS/bildirim log; provider_response JSONB.
"""

import uuid
from sqlalchemy import DateTime, Enum, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import NotificationMessageType, NotificationStatus


class NotificationLog(Base):
    """Bildirim log; message_type ve status ENUM."""

    __tablename__ = "notification_logs"

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
    recipient_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    message_type: Mapped[NotificationMessageType] = mapped_column(
        Enum(NotificationMessageType, name="notificationmessagetype", create_constraint=True),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notificationstatus", create_constraint=True),
        nullable=False,
    )
    provider_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    def __repr__(self) -> str:
        return f"<NotificationLog id={self.id!r} message_type={self.message_type!r} status={self.status!r}>"
