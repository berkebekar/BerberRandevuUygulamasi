"""add tenant whatsapp coexistence fields

Revision ID: 028_add_tenant_whatsapp_coexistence
Revises: 027_add_parent_tenant_id
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "028_add_tenant_whatsapp_coexistence"
down_revision = "027_add_parent_tenant_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("whatsapp_phone_number_id", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("whatsapp_waba_id", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("whatsapp_display_phone_number", sa.String(50), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("whatsapp_connection_status", sa.String(30), nullable=False, server_default="disconnected"),
    )
    op.add_column("tenants", sa.Column("whatsapp_connected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("whatsapp_bot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_unique_constraint(
        "uq_tenants_whatsapp_phone_number_id",
        "tenants",
        ["whatsapp_phone_number_id"],
    )
    op.create_index("idx_tenants_whatsapp_connection_status", "tenants", ["whatsapp_connection_status"])


def downgrade() -> None:
    op.drop_index("idx_tenants_whatsapp_connection_status", table_name="tenants")
    op.drop_constraint("uq_tenants_whatsapp_phone_number_id", "tenants", type_="unique")
    op.drop_column("tenants", "whatsapp_bot_enabled")
    op.drop_column("tenants", "whatsapp_connected_at")
    op.drop_column("tenants", "whatsapp_connection_status")
    op.drop_column("tenants", "whatsapp_display_phone_number")
    op.drop_column("tenants", "whatsapp_waba_id")
    op.drop_column("tenants", "whatsapp_phone_number_id")
