"""merge otp provider and whatsapp reminder heads

Revision ID: 031_merge_otp_provider_and_whatsapp_heads
Revises: 020_add_tenant_otp_provider, 030_add_whatsapp_long_absence_reminders
Create Date: 2026-05-17
"""


revision = "031_merge_otp_provider_and_whatsapp_heads"
down_revision = ("020_add_tenant_otp_provider", "030_add_whatsapp_long_absence_reminders")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
