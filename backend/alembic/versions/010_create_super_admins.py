"""create super_admins table

Revision ID: 010_create_super_admins
Revises: 009_add_slot_duration_minutes_to_day_overrides
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "010_create_super_admins"
down_revision = "009_add_slot_duration_minutes_to_day_overrides"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "super_admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("session_version", sa.String(length=36), nullable=False, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_super_admins_username", "super_admins", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_super_admins_username", table_name="super_admins")
    op.drop_table("super_admins")
