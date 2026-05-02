"""
superadmin/user_service.py - Super admin user management business logic.
"""

import math
import uuid
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, Response
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import resolve_cookie_domain
from app.core.security import create_token
from app.models.booking import Booking
from app.models.enums import OTPRole, UserStatus
from app.models.otp_record import OTPRecord
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.superadmin.activity_helper import append_activity_log
from app.modules.superadmin.user_schemas import (
    SuperAdminTenantSummary,
    SuperAdminUserBlockRequest,
    SuperAdminUserBookingHistory,
    SuperAdminUserBookingHistoryItem,
    SuperAdminUserBookingHistoryPagination,
    SuperAdminUserDetailResponse,
    SuperAdminUserListItem,
    SuperAdminUserListPagination,
    SuperAdminUserListQuery,
    SuperAdminUserListResponse,
    SuperAdminUserOTPItem,
    SuperAdminUserStatusResponse,
)

TZ = ZoneInfo("Europe/Istanbul")
_IMPERSONATION_TTL_SECONDS = 60 * 60
_IMPERSONATION_EXPIRES_MINUTES = 60


def _to_user_status(value) -> UserStatus:
    if isinstance(value, UserStatus):
        return value
    if isinstance(value, str):
        return UserStatus(value)
    return UserStatus.blocked if bool(value) else UserStatus.active


def _sync_user_status(user: User, status: UserStatus) -> None:
    user.status = status
    user.is_blocked = status == UserStatus.blocked


async def _log_activity(
    db: AsyncSession,
    super_admin: SuperAdmin,
    action_type: str,
    user: User,
    metadata_json: dict | None = None,
) -> None:
    await append_activity_log(
        db,
        super_admin=super_admin,
        action_type=action_type,
        entity_type="user",
        entity_id=str(user.id),
        tenant_id=user.tenant_id,
        metadata_json=metadata_json or None,
    )


async def _get_user_or_404(db: AsyncSession, user_id: uuid.UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(404, {"error": "user_not_found"})
    user.status = _to_user_status(getattr(user, "status", None))
    return user


async def list_users(db: AsyncSession, query: SuperAdminUserListQuery) -> SuperAdminUserListResponse:
    booking_agg = (
        select(
            Booking.user_id.label("user_id"),
            func.count(Booking.id).label("booking_count"),
            func.max(Booking.slot_time).label("last_booking_at"),
        )
        .group_by(Booking.user_id)
        .subquery()
    )

    filters = []
    if query.tenant_id:
        filters.append(User.tenant_id == query.tenant_id)
    if query.status:
        filters.append(User.status == query.status)
    if query.search and query.search.strip():
        value = f"%{query.search.strip()}%"
        filters.append(
            or_(
                User.phone.ilike(value),
                User.first_name.ilike(value),
                User.last_name.ilike(value),
            )
        )
    if query.date_from:
        filters.append(User.created_at >= datetime.combine(query.date_from, time.min, tzinfo=TZ))
    if query.date_to:
        filters.append(User.created_at <= datetime.combine(query.date_to, time.max, tzinfo=TZ))

    total_stmt = select(func.count(User.id)).select_from(User).join(Tenant, Tenant.id == User.tenant_id)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total_result = await db.execute(total_stmt)
    total = int(total_result.scalar_one() or 0)
    total_pages = math.ceil(total / query.page_size) if total else 0

    booking_count_col = func.coalesce(booking_agg.c.booking_count, 0)
    last_booking_col = booking_agg.c.last_booking_at
    sort_map = {
        "created_at": User.created_at,
        "phone": User.phone,
        "first_name": User.first_name,
        "last_name": User.last_name,
        "booking_count": booking_count_col,
        "last_booking_at": last_booking_col,
    }
    order_fn = asc if query.sort_order == "asc" else desc
    primary_order = order_fn(sort_map[query.sort_by])
    if query.sort_by == "last_booking_at":
        primary_order = primary_order.nulls_last()

    stmt = (
        select(
            User,
            Tenant,
            booking_count_col.label("booking_count"),
            last_booking_col.label("last_booking_at"),
        )
        .join(Tenant, Tenant.id == User.tenant_id)
        .outerjoin(booking_agg, booking_agg.c.user_id == User.id)
    )
    if filters:
        stmt = stmt.where(*filters)

    rows = await db.execute(
        stmt.order_by(primary_order, desc(User.created_at))
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    )

    items: list[SuperAdminUserListItem] = []
    for user, tenant, booking_count, last_booking_at in rows.all():
        items.append(
            SuperAdminUserListItem(
                id=user.id,
                tenant=SuperAdminTenantSummary(id=tenant.id, subdomain=tenant.subdomain, name=tenant.name),
                phone=user.phone,
                first_name=user.first_name,
                last_name=user.last_name,
                status=_to_user_status(getattr(user, "status", None)),
                is_blocked=bool(getattr(user, "is_blocked", False)),
                created_at=user.created_at,
                booking_count=int(booking_count or 0),
                last_booking_at=last_booking_at,
            )
        )

    return SuperAdminUserListResponse(
        items=items,
        pagination=SuperAdminUserListPagination(
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


async def get_user_detail(
    db: AsyncSession,
    user_id: uuid.UUID,
    booking_page: int,
    booking_page_size: int,
) -> SuperAdminUserDetailResponse:
    user_result = await db.execute(
        select(User, Tenant).join(Tenant, Tenant.id == User.tenant_id).where(User.id == user_id)
    )
    row = user_result.one_or_none()
    if row is None:
        raise HTTPException(404, {"error": "user_not_found"})
    user, tenant = row
    user.status = _to_user_status(getattr(user, "status", None))

    booking_total_result = await db.execute(select(func.count(Booking.id)).where(Booking.user_id == user.id))
    booking_total = int(booking_total_result.scalar_one() or 0)
    booking_total_pages = math.ceil(booking_total / booking_page_size) if booking_total else 0

    booking_rows = await db.execute(
        select(Booking)
        .where(Booking.user_id == user.id)
        .order_by(Booking.slot_time.desc())
        .offset((booking_page - 1) * booking_page_size)
        .limit(booking_page_size)
    )
    booking_items = [
        SuperAdminUserBookingHistoryItem(
            id=booking.id,
            slot_time=booking.slot_time,
            status=booking.status,
            cancelled_by=booking.cancelled_by,
            created_at=booking.created_at,
        )
        for booking in booking_rows.scalars().all()
    ]

    otp_rows = await db.execute(
        select(OTPRecord)
        .where(
            OTPRecord.tenant_id == user.tenant_id,
            OTPRecord.phone == user.phone,
            OTPRecord.role == OTPRole.user,
        )
        .order_by(OTPRecord.created_at.desc())
        .limit(10)
    )
    otp_items = [
        SuperAdminUserOTPItem(
            id=otp.id,
            phone=otp.phone,
            expires_at=otp.expires_at,
            is_used=otp.is_used,
            attempt_count=otp.attempt_count,
            created_at=otp.created_at,
        )
        for otp in otp_rows.scalars().all()
    ]

    return SuperAdminUserDetailResponse(
        id=user.id,
        tenant=SuperAdminTenantSummary(id=tenant.id, subdomain=tenant.subdomain, name=tenant.name),
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        status=user.status,
        is_blocked=bool(getattr(user, "is_blocked", False)),
        created_at=user.created_at,
        bookings=SuperAdminUserBookingHistory(
            items=booking_items,
            pagination=SuperAdminUserBookingHistoryPagination(
                page=booking_page,
                page_size=booking_page_size,
                total=booking_total,
                total_pages=booking_total_pages,
            ),
        ),
        otp_requests=otp_items,
    )


async def block_user(
    db: AsyncSession,
    super_admin: SuperAdmin,
    user_id: uuid.UUID,
    body: SuperAdminUserBlockRequest,
) -> SuperAdminUserStatusResponse:
    user = await _get_user_or_404(db, user_id)
    if user.status == UserStatus.deleted:
        raise HTTPException(409, {"error": "user_deleted"})

    if user.status != UserStatus.blocked:
        _sync_user_status(user, UserStatus.blocked)
        user.session_version = str(uuid.uuid4())
        await _log_activity(
            db,
            super_admin=super_admin,
            action_type="user_blocked",
            user=user,
            metadata_json={"reason": body.reason},
        )
        await db.commit()

    return SuperAdminUserStatusResponse(id=user.id, status=user.status, is_blocked=user.is_blocked)


async def unblock_user(
    db: AsyncSession,
    super_admin: SuperAdmin,
    user_id: uuid.UUID,
) -> SuperAdminUserStatusResponse:
    user = await _get_user_or_404(db, user_id)
    if user.status == UserStatus.deleted:
        raise HTTPException(409, {"error": "user_deleted"})

    if user.status == UserStatus.blocked:
        _sync_user_status(user, UserStatus.active)
        await _log_activity(
            db,
            super_admin=super_admin,
            action_type="user_unblocked",
            user=user,
        )
        await db.commit()

    return SuperAdminUserStatusResponse(id=user.id, status=user.status, is_blocked=user.is_blocked)


async def soft_delete_user(
    db: AsyncSession,
    super_admin: SuperAdmin,
    user_id: uuid.UUID,
) -> SuperAdminUserStatusResponse:
    user = await _get_user_or_404(db, user_id)

    if user.status == UserStatus.deleted:
        return SuperAdminUserStatusResponse(id=user.id, status=user.status, is_blocked=user.is_blocked)

    previous_status = user.status.value
    _sync_user_status(user, UserStatus.deleted)
    user.session_version = str(uuid.uuid4())
    await _log_activity(
        db,
        super_admin=super_admin,
        action_type="user_deleted",
        user=user,
        metadata_json={"previous_status": previous_status, "status": user.status.value},
    )
    await db.commit()
    return SuperAdminUserStatusResponse(id=user.id, status=user.status, is_blocked=user.is_blocked)


async def restore_user(
    db: AsyncSession,
    super_admin: SuperAdmin,
    user_id: uuid.UUID,
) -> SuperAdminUserStatusResponse:
    user = await _get_user_or_404(db, user_id)

    if user.status == UserStatus.deleted:
        _sync_user_status(user, UserStatus.active)
        await _log_activity(
            db,
            super_admin=super_admin,
            action_type="user_restored",
            user=user,
            metadata_json={"status": user.status.value},
        )
        await db.commit()

    return SuperAdminUserStatusResponse(id=user.id, status=user.status, is_blocked=user.is_blocked)


async def start_user_impersonation(
    db: AsyncSession,
    super_admin: SuperAdmin,
    user_id: uuid.UUID,
    request: Request,
    response: Response,
) -> dict:
    user = await _get_user_or_404(db, user_id)
    if user.status == UserStatus.deleted:
        raise HTTPException(409, {"error": "user_deleted"})

    now_epoch = int(datetime.now(timezone.utc).timestamp())
    imp_exp_epoch = now_epoch + _IMPERSONATION_TTL_SECONDS
    token = create_token(
        {
            "sub": str(user.id),
            "role": "user",
            "sv": user.session_version,
            "imp": True,
            "imp_by": str(super_admin.id),
            "imp_tenant": str(user.tenant_id),
            "imp_exp": imp_exp_epoch,
        },
        expires_minutes=_IMPERSONATION_EXPIRES_MINUTES,
    )
    settings = get_settings()
    response.set_cookie(
        key="user_session",
        value=token,
        httponly=True,
        secure=(settings.env == "production"),
        samesite="lax",
        max_age=_IMPERSONATION_TTL_SECONDS,
        domain=resolve_cookie_domain(request),
    )

    await _log_activity(
        db,
        super_admin=super_admin,
        action_type="user_impersonation_started",
        user=user,
        metadata_json={"ttl_seconds": _IMPERSONATION_TTL_SECONDS},
    )
    await db.commit()
    return {"message": "impersonation_started", "expires_in_seconds": _IMPERSONATION_TTL_SECONDS}
