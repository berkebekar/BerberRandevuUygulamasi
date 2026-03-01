"""initial_schema — Tüm tablolar ve ENUM'lar (CLAUDE.md).

Revision ID: 001_initial
Revises:
Create Date: 2026-02-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ENUM tipleri (Booking, OTPRecord, NotificationLog için)
    op.execute("CREATE TYPE bookingstatus AS ENUM ('confirmed', 'cancelled')")
    op.execute("CREATE TYPE cancelledby AS ENUM ('admin', 'user')")
    op.execute("CREATE TYPE otprole AS ENUM ('user', 'admin')")
    op.execute("CREATE TYPE notificationmessagetype AS ENUM ('otp', 'booking_created', 'booking_cancelled')")
    op.execute("CREATE TYPE notificationstatus AS ENUM ('sent', 'failed', 'pending')")

    # Tablolar (FK sırasına göre)
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("subdomain", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_subdomain"), "tenants", ["subdomain"], unique=True)

    op.create_table(
        "admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_admins_email"), "admins", ["email"], unique=True)
    op.create_index(op.f("ix_admins_phone"), "admins", ["phone"], unique=True)
    op.create_index(op.f("ix_admins_tenant_id"), "admins", ["tenant_id"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),
    )

    op.create_table(
        "barber_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("work_start_time", sa.Time(), nullable=False),
        sa.Column("work_end_time", sa.Time(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_barber_profiles_tenant_id"), "barber_profiles", ["tenant_id"], unique=True)

    op.create_table(
        "day_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("work_start_time", sa.Time(), nullable=True),
        sa.Column("work_end_time", sa.Time(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "date", name="uq_day_overrides_tenant_date"),
    )

    op.create_table(
        "slot_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "blocked_at", name="uq_slot_blocks_tenant_blocked_at"),
    )

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", postgresql.ENUM("confirmed", "cancelled", name="bookingstatus", create_type=False), nullable=False),
        sa.Column("cancelled_by", postgresql.ENUM("admin", "user", name="cancelledby", create_type=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Booking partial unique index'ler (CLAUDE.md)
    op.create_index(
        "ix_bookings_tenant_slot_confirmed",
        "bookings",
        ["tenant_id", "slot_time"],
        unique=True,
        postgresql_where=sa.text("status = 'confirmed'"),
    )
    op.execute("""
        CREATE UNIQUE INDEX ix_bookings_tenant_user_date_confirmed
        ON bookings (tenant_id, user_id, CAST(slot_time AT TIME ZONE 'Europe/Istanbul' AS date))
        WHERE status = 'confirmed'
    """)

    op.create_table(
        "otp_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM("user", "admin", name="otprole", create_type=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "notification_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_phone", sa.String(50), nullable=False),
        sa.Column("message_type", postgresql.ENUM("otp", "booking_created", "booking_cancelled", name="notificationmessagetype", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM("sent", "failed", "pending", name="notificationstatus", create_type=False), nullable=False),
        sa.Column("provider_response", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("notification_logs")
    op.drop_table("otp_records")
    op.execute("DROP INDEX IF EXISTS ix_bookings_tenant_user_date_confirmed")
    op.drop_index("ix_bookings_tenant_slot_confirmed", table_name="bookings", postgresql_where=sa.text("status = 'confirmed'"))
    op.drop_table("bookings")
    op.drop_table("slot_blocks")
    op.drop_table("day_overrides")
    op.drop_table("barber_profiles")
    op.drop_table("users")
    op.drop_table("admins")
    op.drop_table("tenants")

    op.execute("DROP TYPE IF EXISTS notificationstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS notificationmessagetype CASCADE")
    op.execute("DROP TYPE IF EXISTS otprole CASCADE")
    op.execute("DROP TYPE IF EXISTS cancelledby CASCADE")
    op.execute("DROP TYPE IF EXISTS bookingstatus CASCADE")
