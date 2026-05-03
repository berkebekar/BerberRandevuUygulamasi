"""remove whatsapp credentials from tenants

Revision ID: 023_remove_tenant_whatsapp_credentials
Revises: 022_add_reminder_sent_to_bookings
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op


revision = "023_remove_tenant_whatsapp_credentials"
down_revision = "022_add_reminder_sent_to_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_tenants_whatsapp_phone_number_id", "tenants", type_="unique", if_exists=True)
    op.drop_column("tenants", "whatsapp_phone_number_id")
    op.drop_column("tenants", "whatsapp_access_token")


def downgrade() -> None:
    op.add_column("tenants", sa.Column("whatsapp_access_token", sa.String(500), nullable=True))
    op.add_column("tenants", sa.Column("whatsapp_phone_number_id", sa.String(100), nullable=True))
