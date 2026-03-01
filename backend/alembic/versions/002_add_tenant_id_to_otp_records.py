"""add tenant_id to otp_records for tenant-scoped otp queries

Revision ID: 002_add_tenant_id_to_otp_records
Revises: 001_initial
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002_add_tenant_id_to_otp_records"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Minimum invasive: nullable=True to avoid backfill requirement on old rows.
    op.add_column(
        "otp_records",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_otp_records_tenant_id_tenants",
        "otp_records",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        "ix_otp_records_tenant_id",
        "otp_records",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_otp_records_tenant_phone_role_used_created",
        "otp_records",
        ["tenant_id", "phone", "role", "is_used", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_otp_records_tenant_phone_role_used_created", table_name="otp_records")
    op.drop_index("ix_otp_records_tenant_id", table_name="otp_records")
    op.drop_constraint("fk_otp_records_tenant_id_tenants", "otp_records", type_="foreignkey")
    op.drop_column("otp_records", "tenant_id")
