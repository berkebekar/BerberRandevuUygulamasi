"""create error_logs table

Revision ID: 012_create_error_logs
Revises: 011_create_activity_logs
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012_create_error_logs"
down_revision = "011_create_activity_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "error_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("request_meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_error_logs_created_at", "error_logs", ["created_at"], unique=False)
    op.create_index("ix_error_logs_tenant_id", "error_logs", ["tenant_id"], unique=False)
    op.create_index("ix_error_logs_status_code", "error_logs", ["status_code"], unique=False)
    op.create_index("ix_error_logs_endpoint", "error_logs", ["endpoint"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_error_logs_endpoint", table_name="error_logs")
    op.drop_index("ix_error_logs_status_code", table_name="error_logs")
    op.drop_index("ix_error_logs_tenant_id", table_name="error_logs")
    op.drop_index("ix_error_logs_created_at", table_name="error_logs")
    op.drop_table("error_logs")
