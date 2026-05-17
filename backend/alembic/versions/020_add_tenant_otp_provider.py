"""add tenant otp provider

Revision ID: 020_add_tenant_otp_provider
Revises: 019_add_tenant_whatsapp
Create Date: 2026-05-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "020_add_tenant_otp_provider"
down_revision = "019_add_tenant_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "otp_provider",
            sa.String(length=30),
            nullable=False,
            server_default="whatsapp",
        ),
    )
    op.create_check_constraint(
        "ck_tenants_otp_provider",
        "tenants",
        "otp_provider IN ('whatsapp', 'firebase_sms')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenants_otp_provider", "tenants", type_="check")
    op.drop_column("tenants", "otp_provider")
