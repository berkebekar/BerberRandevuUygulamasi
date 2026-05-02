"""add whatsapp fields to tenants

Revision ID: 019_add_tenant_whatsapp
Revises: 018_drop_notification_logs
Create Date: 2026-05-02
"""

from alembic import op
import sqlalchemy as sa

revision = "019_add_tenant_whatsapp"
down_revision = "018_drop_notification_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("whatsapp_phone_number_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("whatsapp_access_token", sa.String(500), nullable=True),
    )
    op.create_unique_constraint(
        "uq_tenants_whatsapp_phone_number_id",
        "tenants",
        ["whatsapp_phone_number_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_tenants_whatsapp_phone_number_id", "tenants", type_="unique")
    op.drop_column("tenants", "whatsapp_access_token")
    op.drop_column("tenants", "whatsapp_phone_number_id")
