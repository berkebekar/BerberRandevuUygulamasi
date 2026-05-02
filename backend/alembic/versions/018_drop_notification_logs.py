"""drop notification_logs table and related enum types

Revision ID: 018_drop_notification_logs
Revises: 017_add_monitoring_indexes
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "018_drop_notification_logs"
down_revision = "017_add_monitoring_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("notification_logs")
    op.execute("DROP TYPE IF EXISTS notificationmessagetype")
    op.execute("DROP TYPE IF EXISTS notificationstatus")


def downgrade() -> None:
    notificationmessagetype = postgresql.ENUM(
        "otp", "booking_created", "booking_cancelled",
        name="notificationmessagetype",
    )
    notificationstatus = postgresql.ENUM(
        "sent", "failed", "pending",
        name="notificationstatus",
    )
    notificationmessagetype.create(op.get_bind())
    notificationstatus.create(op.get_bind())

    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("recipient_phone", sa.String(50), nullable=False),
        sa.Column("message_type", sa.Enum(name="notificationmessagetype"), nullable=False),
        sa.Column("status", sa.Enum(name="notificationstatus"), nullable=False),
        sa.Column("provider_response", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
