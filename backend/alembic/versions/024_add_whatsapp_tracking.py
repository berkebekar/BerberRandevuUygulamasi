"""add whatsapp tracking tables and booking source

Revision ID: 024_add_whatsapp_tracking
Revises: 023_remove_tenant_whatsapp_credentials
Create Date: 2026-05-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "024_add_whatsapp_tracking"
down_revision = "023_remove_tenant_whatsapp_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bookings: kaynak bilgisi (web / whatsapp)
    op.add_column(
        "bookings",
        sa.Column("source", sa.String(20), nullable=False, server_default="web"),
    )

    # wa_contact_logs: tenant bazlı benzersiz günlük WA teması
    op.create_table(
        "wa_contact_logs",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(), nullable=False),
        sa.Column("wa_phone", sa.Text(), nullable=False),
        sa.Column("contact_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "wa_phone", "contact_date",
            name="uq_wa_contact_logs_tenant_phone_date",
        ),
    )
    op.create_index("idx_wa_contact_logs_date", "wa_contact_logs", ["contact_date"])
    op.create_index(
        "idx_wa_contact_logs_tenant_date", "wa_contact_logs", ["tenant_id", "contact_date"]
    )

    # wa_error_logs: bot katmanı hata kayıtları
    op.create_table(
        "wa_error_logs",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(), nullable=True),
        sa.Column("wa_phone", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("meta_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_wa_error_logs_tenant_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_wa_error_logs_created_at", "wa_error_logs", ["created_at"])
    op.create_index("idx_wa_error_logs_tenant_id", "wa_error_logs", ["tenant_id"])
    op.create_index("idx_wa_error_logs_error_type", "wa_error_logs", ["error_type"])


def downgrade() -> None:
    op.drop_index("idx_wa_error_logs_error_type", table_name="wa_error_logs")
    op.drop_index("idx_wa_error_logs_tenant_id", table_name="wa_error_logs")
    op.drop_index("idx_wa_error_logs_created_at", table_name="wa_error_logs")
    op.drop_table("wa_error_logs")

    op.drop_index("idx_wa_contact_logs_tenant_date", table_name="wa_contact_logs")
    op.drop_index("idx_wa_contact_logs_date", table_name="wa_contact_logs")
    op.drop_table("wa_contact_logs")

    op.drop_column("bookings", "source")
