"""add status enum to users

Revision ID: 016_add_status_to_users
Revises: 015_add_is_blocked_to_users
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "016_add_status_to_users"
down_revision = "015_add_is_blocked_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_status = postgresql.ENUM("active", "blocked", "deleted", name="userstatus")
    user_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "status",
            user_status,
            nullable=True,
            server_default=sa.text("'active'::userstatus"),
        ),
    )

    op.execute(
        """
        UPDATE users
        SET status = CASE
            WHEN is_blocked = true THEN 'blocked'::userstatus
            ELSE 'active'::userstatus
        END
        """
    )

    op.alter_column("users", "status", nullable=False)
    op.create_index("ix_users_status", "users", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_status", table_name="users")
    op.drop_column("users", "status")
    user_status = postgresql.ENUM("active", "blocked", "deleted", name="userstatus")
    user_status.drop(op.get_bind(), checkfirst=True)
