"""remove daily unique booking constraint for up-to-3 same-day bookings

Revision ID: 005_daily_booking_limit_3
Revises: 004_weekly_closed_days
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


revision = "005_daily_booking_limit_3"
down_revision = "004_weekly_closed_days"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alembic metadata kolonu gelecekte uzun revision id'leri de guvenle saklasin.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    # Gunde 3 randevuya izin vermek icin user+date unique index'ini kaldiriyoruz.
    op.execute("DROP INDEX IF EXISTS ix_bookings_tenant_user_date_confirmed")


def downgrade() -> None:
    # Eski kurala donus: ayni user ayni gunde sadece 1 confirmed randevu alabilsin.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_bookings_tenant_user_date_confirmed
        ON bookings (tenant_id, user_id, CAST(slot_time AT TIME ZONE 'Europe/Istanbul' AS date))
        WHERE status = 'confirmed'
        """
    )

    # Geri donuste eski schema beklentisi icin kolonu tekrar 32'ye indiriyoruz.
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )

