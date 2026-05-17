"""add whatsapp long absence reminders

Revision ID: 030_add_whatsapp_long_absence_reminders
Revises: 029_add_whatsapp_bot_feature_settings
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "030_add_whatsapp_long_absence_reminders"
down_revision = "029_add_whatsapp_bot_feature_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "whatsapp_long_absence_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "whatsapp_long_absence_superadmin_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "whatsapp_long_absence_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("45"),
        ),
    )
    op.create_check_constraint(
        "ck_tenants_whatsapp_long_absence_days",
        "tenants",
        "whatsapp_long_absence_days BETWEEN 30 AND 120",
    )
    op.create_table(
        "wa_long_absence_reminders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "booking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "booking_id", name="uq_wa_long_absence_tenant_booking"),
    )
    op.create_index(
        "ix_wa_long_absence_tenant_user",
        "wa_long_absence_reminders",
        ["tenant_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_wa_long_absence_tenant_user", table_name="wa_long_absence_reminders")
    op.drop_table("wa_long_absence_reminders")
    op.drop_constraint("ck_tenants_whatsapp_long_absence_days", "tenants", type_="check")
    op.drop_column("tenants", "whatsapp_long_absence_days")
    op.drop_column("tenants", "whatsapp_long_absence_superadmin_enabled")
    op.drop_column("tenants", "whatsapp_long_absence_enabled")
