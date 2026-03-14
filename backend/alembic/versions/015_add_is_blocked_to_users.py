"""add is_blocked to users

Revision ID: 015_add_is_blocked_to_users
Revises: 014_add_status_to_tenants
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa


revision = "015_add_is_blocked_to_users"
down_revision = "014_add_status_to_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_users_is_blocked", "users", ["is_blocked"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_is_blocked", table_name="users")
    op.drop_column("users", "is_blocked")
