"""add no_show to bookingstatus enum

Revision ID: 003_add_no_show_status
Revises: 002_add_tenant_id_to_otp_records
Create Date: 2026-03-01
"""

from alembic import op


revision = "003_add_no_show_status"
down_revision = "002_add_tenant_id_to_otp_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'no_show'")


def downgrade() -> None:
    # PostgreSQL enum value remove icin yeni tip olusturup cast ediyoruz.
    op.execute("CREATE TYPE bookingstatus_old AS ENUM ('confirmed', 'cancelled')")
    op.execute(
        """
        ALTER TABLE bookings
        ALTER COLUMN status TYPE bookingstatus_old
        USING (
            CASE
                WHEN status::text = 'no_show' THEN 'confirmed'
                ELSE status::text
            END
        )::bookingstatus_old
        """
    )
    op.execute("DROP TYPE bookingstatus")
    op.execute("ALTER TYPE bookingstatus_old RENAME TO bookingstatus")
