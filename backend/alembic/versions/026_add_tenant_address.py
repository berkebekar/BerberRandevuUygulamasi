"""026_add_tenant_address

Revision ID: 026_add_tenant_address
Revises: 025_remove_admin_password_hash
Create Date: 2026-05-10
"""

from alembic import op
import sqlalchemy as sa

revision = "026_add_tenant_address"
down_revision = "025_remove_admin_password_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("address", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "address")
