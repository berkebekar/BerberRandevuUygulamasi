"""add whatsapp bot feature settings

Revision ID: 029_add_whatsapp_bot_feature_settings
Revises: 028_add_tenant_whatsapp_coexistence
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa


revision = "029_add_whatsapp_bot_feature_settings"
down_revision = "028_add_tenant_whatsapp_coexistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bool_default = sa.text("true")
    op.add_column(
        "tenants",
        sa.Column("whatsapp_bot_superadmin_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_booking_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_booking_superadmin_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_reminder_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_reminder_superadmin_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_cancellation_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_cancellation_superadmin_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_reschedule_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_reschedule_superadmin_enabled", sa.Boolean(), nullable=False, server_default=bool_default),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_silent_numbers", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("tenants", "whatsapp_silent_numbers")
    op.drop_column("tenants", "whatsapp_reschedule_superadmin_enabled")
    op.drop_column("tenants", "whatsapp_reschedule_enabled")
    op.drop_column("tenants", "whatsapp_cancellation_superadmin_enabled")
    op.drop_column("tenants", "whatsapp_cancellation_enabled")
    op.drop_column("tenants", "whatsapp_reminder_superadmin_enabled")
    op.drop_column("tenants", "whatsapp_reminder_enabled")
    op.drop_column("tenants", "whatsapp_booking_superadmin_enabled")
    op.drop_column("tenants", "whatsapp_booking_enabled")
    op.drop_column("tenants", "whatsapp_bot_superadmin_enabled")
