"""add rescheduled_by values to cancelledby enum

Revision ID: 020_add_reschedule_to_cancelled_by
Revises: 019_add_tenant_whatsapp
Create Date: 2026-05-03
"""

from alembic import op


revision = "020_add_reschedule_to_cancelled_by"
down_revision = "019_add_tenant_whatsapp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE cancelledby ADD VALUE IF NOT EXISTS 'rescheduled_by_user'")
    op.execute("ALTER TYPE cancelledby ADD VALUE IF NOT EXISTS 'rescheduled_by_admin'")


def downgrade() -> None:
    # PostgreSQL'de enum degerini silmek desteklenmez; downgrade atlanir.
    pass
