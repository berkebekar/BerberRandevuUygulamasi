"""add slot_duration_minutes to day_overrides

Revision ID: 009_add_slot_duration_minutes_to_day_overrides
Revises: 008_add_max_booking_days_ahead
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa


revision = "009_add_slot_duration_minutes_to_day_overrides"
down_revision = "008_add_max_booking_days_ahead"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "day_overrides",
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("day_overrides", "slot_duration_minutes")
