"""
superadmin/stats_service.py - Platform geneli dashboard istatistik servisleri.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.booking import Booking
from app.models.enums import BookingStatus, TenantStatus
from app.models.error_log import ErrorLog
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.superadmin.stats_schemas import (
    OverviewBookingStats,
    OverviewCancelStats,
    OverviewTenantStats,
    OverviewUserStats,
    RecentActivityItem,
    SuperAdminOverviewResponse,
    SuperAdminRecentActivitiesResponse,
    SuperAdminTrendsResponse,
    TrendPoint,
)

TZ = ZoneInfo("Europe/Istanbul")


def _month_start_local(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, 1, 0, 0, 0, tzinfo=TZ)


def _next_month_start_local(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1, 0, 0, 0, tzinfo=TZ)
    return datetime(dt.year, dt.month + 1, 1, 0, 0, 0, tzinfo=TZ)


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    base = year * 12 + (month - 1) + delta
    return base // 12, (base % 12) + 1


def _month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


async def get_overview_stats(db: AsyncSession) -> SuperAdminOverviewResponse:
    now_local = datetime.now(TZ)
    month_start_local = _month_start_local(now_local)
    next_month_start_local = _next_month_start_local(now_local)
    month_start_utc = month_start_local.astimezone(timezone.utc)
    next_month_start_utc = next_month_start_local.astimezone(timezone.utc)

    tenant_rows = await db.execute(
        select(Tenant.status, func.count(Tenant.id)).group_by(Tenant.status)
    )
    tenant_counts = {status: int(count) for status, count in tenant_rows.all()}

    user_total_result = await db.execute(select(func.count(User.id)))
    user_total = int(user_total_result.scalar_one() or 0)

    booking_counts_result = await db.execute(
        select(
            func.count(Booking.id).label("total_bookings"),
            func.count(Booking.id)
            .filter(Booking.status == BookingStatus.cancelled)
            .label("cancelled_bookings"),
        ).where(
            Booking.created_at >= month_start_utc,
            Booking.created_at < next_month_start_utc,
        )
    )
    booking_counts_row = booking_counts_result.one()
    total_bookings = int(booking_counts_row.total_bookings or 0)
    cancelled_bookings = int(booking_counts_row.cancelled_bookings or 0)
    cancel_rate = round((cancelled_bookings / total_bookings) * 100, 1) if total_bookings else 0.0

    return SuperAdminOverviewResponse(
        tenants=OverviewTenantStats(
            total=int(sum(tenant_counts.values())),
            active=int(tenant_counts.get(TenantStatus.active, 0)),
            inactive=int(tenant_counts.get(TenantStatus.inactive, 0)),
            deleted=int(tenant_counts.get(TenantStatus.deleted, 0)),
        ),
        users=OverviewUserStats(total=user_total),
        bookings=OverviewBookingStats(this_month_total=total_bookings),
        cancel=OverviewCancelStats(
            this_month_cancelled=cancelled_bookings,
            this_month_cancel_rate=cancel_rate,
        ),
    )


async def _get_month_series(
    db: AsyncSession,
    date_column,
    model,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[str, int]:
    month_bucket = func.date_trunc("month", func.timezone("Europe/Istanbul", date_column))
    result = await db.execute(
        select(month_bucket.label("month_bucket"), func.count())
        .select_from(model)
        .where(
            date_column >= start_utc,
            date_column < end_utc,
        )
        .group_by(month_bucket)
        .order_by(month_bucket.asc())
    )
    rows = result.all()
    month_map: dict[str, int] = {}
    for row in rows:
        month_bucket, count_value = row[0], row[1]
        month_map[_month_key(month_bucket)] = int(count_value)
    return month_map


async def get_trends_stats(db: AsyncSession) -> SuperAdminTrendsResponse:
    now_local = datetime.now(TZ)
    current_month_start = _month_start_local(now_local)
    start_year, start_month = _add_months(current_month_start.year, current_month_start.month, -5)
    range_start_local = datetime(start_year, start_month, 1, 0, 0, 0, tzinfo=TZ)
    range_end_local = _next_month_start_local(current_month_start)

    range_start_utc = range_start_local.astimezone(timezone.utc)
    range_end_utc = range_end_local.astimezone(timezone.utc)

    booking_map = await _get_month_series(
        db=db,
        date_column=Booking.created_at,
        model=Booking,
        start_utc=range_start_utc,
        end_utc=range_end_utc,
    )
    tenant_map = await _get_month_series(
        db=db,
        date_column=Tenant.created_at,
        model=Tenant,
        start_utc=range_start_utc,
        end_utc=range_end_utc,
    )
    user_map = await _get_month_series(
        db=db,
        date_column=User.created_at,
        model=User,
        start_utc=range_start_utc,
        end_utc=range_end_utc,
    )

    months: list[str] = []
    for i in range(6):
        year, month = _add_months(range_start_local.year, range_start_local.month, i)
        months.append(f"{year:04d}-{month:02d}")

    return SuperAdminTrendsResponse(
        bookings_per_month=[TrendPoint(month=month, count=int(booking_map.get(month, 0))) for month in months],
        new_tenants_per_month=[TrendPoint(month=month, count=int(tenant_map.get(month, 0))) for month in months],
        new_users_per_month=[TrendPoint(month=month, count=int(user_map.get(month, 0))) for month in months],
    )


def _activity_to_recent_item(activity: ActivityLog) -> RecentActivityItem:
    return RecentActivityItem(
        source="activity_log",
        type=activity.action_type,
        title=activity.action_type,
        description=f"{activity.entity_type}:{activity.entity_id}" if activity.entity_id else activity.entity_type,
        tenant_id=str(activity.tenant_id) if activity.tenant_id else None,
        actor_id=str(activity.super_admin_id) if activity.super_admin_id else None,
        created_at=activity.created_at,
        meta=activity.metadata_json,
    )


def _error_to_recent_item(error_log: ErrorLog) -> RecentActivityItem:
    return RecentActivityItem(
        source="error_log",
        type="error",
        title=f"{error_log.method} {error_log.endpoint} ({error_log.status_code})",
        description=error_log.message,
        tenant_id=str(error_log.tenant_id) if error_log.tenant_id else None,
        actor_id=None,
        created_at=error_log.created_at,
        meta={
            "status_code": error_log.status_code,
            "error_code": error_log.error_code,
            "request_id": error_log.request_id,
        },
    )


async def get_recent_activities(db: AsyncSession, limit: int = 20) -> SuperAdminRecentActivitiesResponse:
    safe_limit = max(1, min(int(limit), 100))
    now_utc = datetime.now(timezone.utc)
    since_24h = now_utc - timedelta(hours=24)

    activity_result = await db.execute(
        select(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(safe_limit)
    )
    error_result = await db.execute(
        select(ErrorLog)
        .where(ErrorLog.created_at >= since_24h)
        .order_by(ErrorLog.created_at.desc())
        .limit(safe_limit)
    )

    recent_items = [
        *[_activity_to_recent_item(item) for item in activity_result.scalars().all()],
        *[_error_to_recent_item(item) for item in error_result.scalars().all()],
    ]
    recent_items.sort(key=lambda item: item.created_at, reverse=True)

    return SuperAdminRecentActivitiesResponse(items=recent_items[:safe_limit])
