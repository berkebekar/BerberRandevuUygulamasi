"""add max_booking_days_ahead to barber_profiles

Revision ID: 008_add_max_booking_days_ahead
Revises: 007_session_version_auth
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


revision = "008_add_max_booking_days_ahead"
down_revision = "007_session_version_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "barber_profiles",
        sa.Column(
            "max_booking_days_ahead",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("14"),
        ),
    )


def downgrade() -> None:
    op.drop_column("barber_profiles", "max_booking_days_ahead")
