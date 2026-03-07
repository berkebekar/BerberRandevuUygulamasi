"""add session_version columns for single-session auth invalidation

Revision ID: 007_session_version_auth
Revises: 006_bookings_tenant_slot_index
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa


revision = "007_session_version_auth"
down_revision = "006_bookings_tenant_slot_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tek cihaz oturum kontrolu icin her user/admin kaydina session_version eklenir.
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            sa.String(length=36),
            nullable=False,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
    )
    op.add_column(
        "admins",
        sa.Column(
            "session_version",
            sa.String(length=36),
            nullable=False,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
    )


def downgrade() -> None:
    op.drop_column("admins", "session_version")
    op.drop_column("users", "session_version")
