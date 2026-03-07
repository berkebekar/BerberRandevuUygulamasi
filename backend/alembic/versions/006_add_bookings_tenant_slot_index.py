"""add non-partial index for bookings tenant/day range scans

Revision ID: 006_bookings_tenant_slot_index
Revises: 005_daily_booking_limit_3
Create Date: 2026-03-07
"""

from alembic import op


revision = "006_bookings_tenant_slot_index"
down_revision = "005_daily_booking_limit_3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Admin gunluk liste sorgulari tum status'leri okur.
    # Bu indeks, tenant + slot_time aralik taramalarini hizlandirir.
    op.create_index(
        "ix_bookings_tenant_slot_time",
        "bookings",
        ["tenant_id", "slot_time"],
        unique=False,
    )


def downgrade() -> None:
    # Geri donuste sadece bu migration'in ekledigi indeksi kaldir.
    op.drop_index("ix_bookings_tenant_slot_time", table_name="bookings")
