"""create activity_logs table

Revision ID: 011_create_activity_logs
Revises: 010_create_super_admins
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "011_create_activity_logs"
down_revision = "010_create_super_admins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("super_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["super_admin_id"], ["super_admins.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_logs_created_at", "activity_logs", ["created_at"], unique=False)
    op.create_index("ix_activity_logs_tenant_id", "activity_logs", ["tenant_id"], unique=False)
    op.create_index("ix_activity_logs_action_type", "activity_logs", ["action_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_logs_action_type", table_name="activity_logs")
    op.drop_index("ix_activity_logs_tenant_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")
    op.drop_table("activity_logs")
