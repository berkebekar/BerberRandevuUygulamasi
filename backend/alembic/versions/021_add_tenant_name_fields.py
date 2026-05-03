"""add first_name last_name to tenants

Revision ID: 021_add_tenant_name_fields
Revises: 020_add_reschedule_to_cancelled_by
Create Date: 2026-05-03
"""

import sqlalchemy as sa
from alembic import op


revision = "021_add_tenant_name_fields"
down_revision = "020_add_reschedule_to_cancelled_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("first_name", sa.String(100), nullable=True))
    op.add_column("tenants", sa.Column("last_name", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "last_name")
    op.drop_column("tenants", "first_name")
