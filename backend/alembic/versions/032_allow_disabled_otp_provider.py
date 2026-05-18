"""allow disabled otp provider

Revision ID: 032_allow_disabled_otp_provider
Revises: 031_merge_otp_provider_and_whatsapp_heads
Create Date: 2026-05-18 00:00:00.000000
"""

from alembic import op


revision = "032_allow_disabled_otp_provider"
down_revision = "031_merge_otp_provider_and_whatsapp_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_tenants_otp_provider", "tenants", type_="check")
    op.create_check_constraint(
        "ck_tenants_otp_provider",
        "tenants",
        "otp_provider IN ('whatsapp', 'firebase_sms', 'disabled')",
    )


def downgrade() -> None:
    op.execute("UPDATE tenants SET otp_provider = 'whatsapp' WHERE otp_provider = 'disabled'")
    op.drop_constraint("ck_tenants_otp_provider", "tenants", type_="check")
    op.create_check_constraint(
        "ck_tenants_otp_provider",
        "tenants",
        "otp_provider IN ('whatsapp', 'firebase_sms')",
    )
