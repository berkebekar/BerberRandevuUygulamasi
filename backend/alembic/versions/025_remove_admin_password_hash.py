"""025_remove_admin_password_hash

Revision ID: 025_remove_admin_password_hash
Revises: 024_add_whatsapp_tracking
Create Date: 2026-05-04

Admin şifre girişi kaldırıldı; admins.password_hash kolonu artık kullanılmıyor.
"""

from alembic import op
import sqlalchemy as sa

revision = "025_remove_admin_password_hash"
down_revision = "024_add_whatsapp_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("admins", "password_hash")


def downgrade() -> None:
    op.add_column(
        "admins",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )
