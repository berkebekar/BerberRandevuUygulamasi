"""create uptime_checks table

Revision ID: 013_create_uptime_checks
Revises: 012_create_error_logs
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013_create_uptime_checks"
down_revision = "012_create_error_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uptime_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("service_name", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_uptime_checks_service_name_checked_at", "uptime_checks", ["service_name", "checked_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_uptime_checks_service_name_checked_at", table_name="uptime_checks")
    op.drop_table("uptime_checks")
