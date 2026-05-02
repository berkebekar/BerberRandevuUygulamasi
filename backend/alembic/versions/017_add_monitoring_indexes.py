"""add indexes for superadmin monitoring queries

Revision ID: 017_add_monitoring_indexes
Revises: 016_add_status_to_users
Create Date: 2026-03-15
"""

from alembic import op


revision = "017_add_monitoring_indexes"
down_revision = "016_add_status_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_created_at ON error_logs (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_tenant_created ON error_logs (tenant_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_status_created ON error_logs (status_code, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_error_code_created ON error_logs (error_code, created_at)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_created_at ON activity_logs (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_action_created ON activity_logs (action_type, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_tenant_created ON activity_logs (tenant_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_activity_logs_sa_created ON activity_logs (super_admin_id, created_at)")


def downgrade() -> None:
    op.drop_index("ix_activity_logs_sa_created", table_name="activity_logs")
    op.drop_index("ix_activity_logs_tenant_created", table_name="activity_logs")
    op.drop_index("ix_activity_logs_action_created", table_name="activity_logs")
    op.drop_index("ix_activity_logs_created_at", table_name="activity_logs")

    op.drop_index("ix_error_logs_error_code_created", table_name="error_logs")
    op.drop_index("ix_error_logs_status_created", table_name="error_logs")
    op.drop_index("ix_error_logs_tenant_created", table_name="error_logs")
    op.drop_index("ix_error_logs_created_at", table_name="error_logs")
