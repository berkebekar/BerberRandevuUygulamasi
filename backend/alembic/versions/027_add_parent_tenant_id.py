"""add parent_tenant_id to tenants

Revision ID: 027_add_parent_tenant_id
Revises: 026_add_tenant_address
Create Date: 2026-05-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "027_add_parent_tenant_id"
down_revision = "026_add_tenant_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("parent_tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_tenants_parent_tenant_id",
        "tenants",
        "tenants",
        ["parent_tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tenants_parent_tenant_id", "tenants", ["parent_tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_parent_tenant_id", table_name="tenants")
    op.drop_constraint("fk_tenants_parent_tenant_id", "tenants", type_="foreignkey")
    op.drop_column("tenants", "parent_tenant_id")
