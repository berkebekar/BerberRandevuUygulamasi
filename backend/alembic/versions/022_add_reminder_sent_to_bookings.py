"""add reminder_sent to bookings

Revision ID: 022_add_reminder_sent_to_bookings
Revises: 021_add_tenant_name_fields
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op


revision = "022_add_reminder_sent_to_bookings"
down_revision = "021_add_tenant_name_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "bookings",
        sa.Column(
            "reminder_sent",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("bookings", "reminder_sent")
