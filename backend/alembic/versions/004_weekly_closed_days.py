"""add weekly closed days to barber profile

Revision ID: 004_weekly_closed_days
Revises: 003_add_no_show_status
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

revision = "004_weekly_closed_days"
down_revision = "003_add_no_show_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "barber_profiles",
        sa.Column(
            "weekly_closed_days",
            sa.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{}'::integer[]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("barber_profiles", "weekly_closed_days")
