"""add status enum to tenants

Revision ID: 014_add_status_to_tenants
Revises: 013_create_uptime_checks
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "014_add_status_to_tenants"
down_revision = "013_create_uptime_checks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tenant_status = postgresql.ENUM("active", "inactive", "deleted", name="tenantstatus")
    tenant_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "tenants",
        sa.Column(
            "status",
            tenant_status,
            nullable=True,
            server_default=sa.text("'active'::tenantstatus"),
        ),
    )

    op.execute(
        """
        UPDATE tenants
        SET status = CASE
            WHEN is_active = true THEN 'active'::tenantstatus
            ELSE 'inactive'::tenantstatus
        END
        """
    )

    op.alter_column("tenants", "status", nullable=False)
    op.create_index("ix_tenants_status", "tenants", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenants_status", table_name="tenants")
    op.drop_column("tenants", "status")
    tenant_status = postgresql.ENUM("active", "inactive", "deleted", name="tenantstatus")
    tenant_status.drop(op.get_bind(), checkfirst=True)
