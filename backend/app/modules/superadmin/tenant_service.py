"""
superadmin/tenant_service.py - Tenant management business logic.
"""

import math
import re
import uuid
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import asc, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.phone import normalize_tr_phone
from app.models.activity_log import ActivityLog
from app.models.admin import Admin
from app.models.barber_profile import BarberProfile
from app.models.booking import Booking
from app.models.day_override import DayOverride
from app.models.enums import BookingStatus, TenantStatus
from app.models.error_log import ErrorLog
from app.models.otp_record import OTPRecord
from app.models.slot_block import SlotBlock
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.models.user import User
from app.models.wa_contact_log import WaContactLog
from app.models.wa_error_log import WaErrorLog
from app.modules.superadmin.tenant_schemas import (
    TenantParentCandidate,
    TenantParentCandidatesResponse,
    TenantAdminSummary,
    TenantCreateRequest,
    TenantCreateResponse,
    TenantDefaultsInput,
    TenantDetailResponse,
    TenantDetailStats,
    TenantDomainSyncResponse,
    TenantHardDeleteResponse,
    TenantListItem,
    TenantListPagination,
    TenantListQuery,
    TenantListResponse,
    TenantParentSummary,
    TenantStatusUpdateRequest,
    TenantStatusUpdateResponse,
    TenantUpdateRequest,
    TenantWhatsappSettings,
    TenantWhatsappUpdateRequest,
)
from app.modules.whatsapp.settings import build_whatsapp_feature_settings, normalize_silent_numbers

TZ = ZoneInfo("Europe/Istanbul")
_SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")


def _normalize_subdomain(subdomain: str) -> str:
    return (subdomain or "").strip().lower()


def _validate_subdomain(subdomain: str) -> str:
    normalized = _normalize_subdomain(subdomain)
    if not _SUBDOMAIN_RE.match(normalized):
        raise HTTPException(422, {"error": "subdomain_invalid"})
    return normalized


def _validate_phone(phone: str) -> str:
    normalized = normalize_tr_phone(phone)
    digits = "".join(ch for ch in normalized if ch.isdigit())
    if len(digits) != 12 or not digits.startswith("90"):
        raise HTTPException(422, {"error": "phone_invalid"})
    return f"+{digits}"


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _map_integrity_error_to_http(exc: IntegrityError) -> HTTPException | None:
    message = str(exc.orig).lower() if getattr(exc, "orig", None) else str(exc).lower()
    if "tenants" in message and "subdomain" in message:
        return HTTPException(409, {"error": "subdomain_already_exists"})
    if "admins" in message and "email" in message:
        return HTTPException(409, {"error": "admin_email_already_exists"})
    if "admins" in message and "phone" in message:
        return HTTPException(409, {"error": "admin_phone_already_exists"})
    return None


def _month_bounds_utc() -> tuple[datetime, datetime]:
    now_local = datetime.now(TZ)
    month_start = datetime(now_local.year, now_local.month, 1, tzinfo=TZ)
    if now_local.month == 12:
        next_month = datetime(now_local.year + 1, 1, 1, tzinfo=TZ)
    else:
        next_month = datetime(now_local.year, now_local.month + 1, 1, tzinfo=TZ)
    return month_start.astimezone(timezone.utc), next_month.astimezone(timezone.utc)


async def _log_activity(
    db: AsyncSession,
    super_admin: SuperAdmin,
    action_type: str,
    tenant_id: uuid.UUID | None,
    metadata: dict | None = None,
) -> None:
    db.add(
        ActivityLog(
            super_admin_id=super_admin.id,
            action_type=action_type,
            entity_type="tenant",
            entity_id=str(tenant_id) if tenant_id else None,
            tenant_id=tenant_id,
            metadata_json=metadata or None,
        )
    )


def _domain_sync_response(
    subdomain: str,
) -> TenantDomainSyncResponse:
    settings = get_settings()
    domain = None
    app_domain = settings.app_domain.strip().lower()
    if app_domain:
        domain = f"https://{subdomain.strip().lower()}.{app_domain}"

    return TenantDomainSyncResponse(
        enabled=True,
        updated=False,
        deploy_requested=False,
        reason="wildcard_domain_strategy",
        domain=domain,
        domains=[domain] if domain else [],
        tenant_count=1,
        error=None,
    )


def _tenant_item(tenant: Tenant, user_count: int, booking_count: int) -> TenantListItem:
    return TenantListItem(
        id=tenant.id,
        parent_tenant_id=getattr(tenant, "parent_tenant_id", None),
        subdomain=tenant.subdomain,
        name=tenant.name,
        address=tenant.address,
        status=tenant.status,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        user_count=int(user_count),
        booking_count=int(booking_count),
    )


def _tenant_parent_summary(tenant: Tenant | None) -> TenantParentSummary | None:
    if tenant is None:
        return None
    return TenantParentSummary(
        id=tenant.id,
        subdomain=tenant.subdomain,
        name=tenant.name,
        first_name=tenant.first_name,
        last_name=tenant.last_name,
    )


def _tenant_whatsapp_settings(tenant: Tenant) -> TenantWhatsappSettings:
    features = build_whatsapp_feature_settings(tenant)
    return TenantWhatsappSettings(
        phone_number_id=getattr(tenant, "whatsapp_phone_number_id", None),
        waba_id=getattr(tenant, "whatsapp_waba_id", None),
        display_phone_number=getattr(tenant, "whatsapp_display_phone_number", None),
        connection_status=getattr(tenant, "whatsapp_connection_status", "disconnected"),
        connected_at=getattr(tenant, "whatsapp_connected_at", None),
        **features.as_dict(),
    )


async def _tenant_has_children(db: AsyncSession, tenant_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Tenant.id).where(
            Tenant.parent_tenant_id == tenant_id,
            Tenant.status != TenantStatus.deleted,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _validate_parent_tenant_assignment(
    db: AsyncSession,
    tenant_id: uuid.UUID | None,
    parent_tenant_id: uuid.UUID | None,
) -> None:
    if parent_tenant_id is None:
        return
    if tenant_id is not None and parent_tenant_id == tenant_id:
        raise HTTPException(422, {"error": "tenant_parent_self"})

    parent_result = await db.execute(select(Tenant).where(Tenant.id == parent_tenant_id))
    parent = parent_result.scalar_one_or_none()
    if parent is None or parent.status != TenantStatus.active or not parent.is_active:
        raise HTTPException(422, {"error": "tenant_parent_invalid"})
    if parent.parent_tenant_id is not None:
        raise HTTPException(422, {"error": "tenant_parent_is_child"})
    if tenant_id is not None and await _tenant_has_children(db, tenant_id):
        raise HTTPException(422, {"error": "tenant_has_children"})


async def list_parent_candidates(
    db: AsyncSession,
    exclude_tenant_id: uuid.UUID | None = None,
) -> TenantParentCandidatesResponse:
    query = select(Tenant).where(
        Tenant.parent_tenant_id.is_(None),
        Tenant.status == TenantStatus.active,
        Tenant.is_active == True,  # noqa: E712
    )
    if exclude_tenant_id is not None:
        query = query.where(Tenant.id != exclude_tenant_id)
    result = await db.execute(query.order_by(Tenant.name.asc(), Tenant.created_at.desc()))
    tenants = list(result.scalars().all())
    return TenantParentCandidatesResponse(
        items=[
            TenantParentCandidate(
                id=tenant.id,
                subdomain=tenant.subdomain,
                name=tenant.name,
                first_name=tenant.first_name,
                last_name=tenant.last_name,
            )
            for tenant in tenants
        ]
    )


async def list_tenants(db: AsyncSession, query: TenantListQuery) -> TenantListResponse:
    filters = []
    if query.status:
        filters.append(Tenant.status == query.status)
    if query.search and query.search.strip():
        value = f"%{query.search.strip()}%"
        filters.append(or_(Tenant.subdomain.ilike(value), Tenant.name.ilike(value)))
    if query.date_from:
        filters.append(Tenant.created_at >= datetime.combine(query.date_from, time.min, tzinfo=TZ))
    if query.date_to:
        filters.append(Tenant.created_at <= datetime.combine(query.date_to, time.max, tzinfo=TZ))

    total_query = select(func.count(Tenant.id))
    if filters:
        total_query = total_query.where(*filters)
    total_result = await db.execute(total_query)
    total = int(total_result.scalar_one() or 0)
    total_pages = math.ceil(total / query.page_size) if total else 0

    sort_map = {
        "created_at": Tenant.created_at,
        "name": Tenant.name,
        "subdomain": Tenant.subdomain,
    }
    order_fn = asc if query.sort_order == "asc" else desc

    if query.sort_by in {"user_count", "booking_count"}:
        user_counts = (
            select(User.tenant_id.label("tenant_id"), func.count(User.id).label("user_count"))
            .group_by(User.tenant_id)
            .subquery()
        )
        booking_counts = (
            select(Booking.tenant_id.label("tenant_id"), func.count(Booking.id).label("booking_count"))
            .group_by(Booking.tenant_id)
            .subquery()
        )
        count_sort_map = {
            "user_count": func.coalesce(user_counts.c.user_count, 0),
            "booking_count": func.coalesce(booking_counts.c.booking_count, 0),
        }
        query_stmt = (
            select(
                Tenant,
                func.coalesce(user_counts.c.user_count, 0).label("user_count"),
                func.coalesce(booking_counts.c.booking_count, 0).label("booking_count"),
            )
            .outerjoin(user_counts, user_counts.c.tenant_id == Tenant.id)
            .outerjoin(booking_counts, booking_counts.c.tenant_id == Tenant.id)
        )
        if filters:
            query_stmt = query_stmt.where(*filters)
        rows = await db.execute(
            query_stmt
            .order_by(order_fn(count_sort_map[query.sort_by]), desc(Tenant.created_at))
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        items = [_tenant_item(tenant, user_count, booking_count) for tenant, user_count, booking_count in rows.all()]
    else:
        tenant_query = select(Tenant)
        if filters:
            tenant_query = tenant_query.where(*filters)
        tenant_rows = await db.execute(
            tenant_query
            .order_by(order_fn(sort_map[query.sort_by]), desc(Tenant.created_at))
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        tenants = list(tenant_rows.scalars().all())
        if not tenants:
            items = []
        else:
            tenant_ids = [tenant.id for tenant in tenants]
            user_counts_rows = await db.execute(
                select(User.tenant_id, func.count(User.id))
                .where(User.tenant_id.in_(tenant_ids))
                .group_by(User.tenant_id)
            )
            booking_counts_rows = await db.execute(
                select(Booking.tenant_id, func.count(Booking.id))
                .where(Booking.tenant_id.in_(tenant_ids))
                .group_by(Booking.tenant_id)
            )
            user_counts_map = {tenant_id: int(count) for tenant_id, count in user_counts_rows.all()}
            booking_counts_map = {tenant_id: int(count) for tenant_id, count in booking_counts_rows.all()}
            items = [
                _tenant_item(
                    tenant,
                    user_count=user_counts_map.get(tenant.id, 0),
                    booking_count=booking_counts_map.get(tenant.id, 0),
                )
                for tenant in tenants
            ]

    return TenantListResponse(
        items=items,
        pagination=TenantListPagination(
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


async def get_tenant_detail(db: AsyncSession, tenant_id: uuid.UUID) -> TenantDetailResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})

    admin_result = await db.execute(select(Admin).where(Admin.tenant_id == tenant.id))
    admin = admin_result.scalar_one_or_none()
    parent = None
    tenant_parent_id = getattr(tenant, "parent_tenant_id", None)
    if tenant_parent_id is not None:
        parent_result = await db.execute(select(Tenant).where(Tenant.id == tenant_parent_id))
        parent = parent_result.scalar_one_or_none()

    user_count_result = await db.execute(select(func.count(User.id)).where(User.tenant_id == tenant.id))
    user_count = int(user_count_result.scalar_one() or 0)

    booking_counts_result = await db.execute(
        select(
            func.count(Booking.id).label("total"),
            func.count(Booking.id).filter(Booking.status == BookingStatus.cancelled).label("cancelled"),
        ).where(Booking.tenant_id == tenant.id)
    )
    booking_counts = booking_counts_result.one()
    booking_total = int(booking_counts.total or 0)
    cancelled = int(booking_counts.cancelled or 0)

    month_start, month_end = _month_bounds_utc()
    month_result = await db.execute(
        select(func.count(Booking.id)).where(
            Booking.tenant_id == tenant.id,
            Booking.created_at >= month_start,
            Booking.created_at < month_end,
        )
    )
    booking_this_month = int(month_result.scalar_one() or 0)

    admin_summary = None
    if admin:
        admin_summary = TenantAdminSummary(
            id=admin.id,
            email=admin.email,
            phone=admin.phone,
            created_at=admin.created_at,
        )

    cancel_rate = round((cancelled / booking_total) * 100, 1) if booking_total else 0.0
    return TenantDetailResponse(
        id=tenant.id,
        parent_tenant_id=tenant_parent_id,
        subdomain=tenant.subdomain,
        name=tenant.name,
        address=tenant.address,
        status=tenant.status,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        admin=admin_summary,
        parent_tenant=_tenant_parent_summary(parent),
        otp_provider=getattr(tenant, "otp_provider", "whatsapp"),
        whatsapp=_tenant_whatsapp_settings(tenant),
        stats=TenantDetailStats(
            user_count=user_count,
            booking_count_total=booking_total,
            booking_count_this_month=booking_this_month,
            cancel_rate=cancel_rate,
        ),
    )


async def create_tenant(
    db: AsyncSession,
    super_admin: SuperAdmin,
    body: TenantCreateRequest,
) -> TenantCreateResponse:
    subdomain = _validate_subdomain(body.subdomain)
    phone = _validate_phone(body.admin_phone)
    defaults = body.defaults or TenantDefaultsInput()

    existing_tenant_result = await db.execute(select(Tenant.id).where(Tenant.subdomain == subdomain))
    if existing_tenant_result.scalar_one_or_none() is not None:
        raise HTTPException(409, {"error": "subdomain_already_exists"})

    normalized_email = _normalize_email(body.admin_email)
    existing_email_result = await db.execute(select(Admin.id).where(Admin.email == normalized_email))
    if existing_email_result.scalar_one_or_none() is not None:
        raise HTTPException(409, {"error": "admin_email_already_exists"})

    existing_phone_result = await db.execute(select(Admin.id).where(Admin.phone == phone))
    if existing_phone_result.scalar_one_or_none() is not None:
        raise HTTPException(409, {"error": "admin_phone_already_exists"})
    await _validate_parent_tenant_assignment(db, None, body.parent_tenant_id)

    tenant = Tenant(
        parent_tenant_id=body.parent_tenant_id,
        subdomain=subdomain,
        name=body.name.strip(),
        address=body.address.strip(),
        first_name=body.admin_first_name.strip(),
        last_name=body.admin_last_name.strip(),
        is_active=True,
        status=TenantStatus.active,
    )
    admin = None

    try:
        db.add(tenant)
        await db.flush()

        admin = Admin(
            tenant_id=tenant.id,
            email=normalized_email,
            phone=phone,
        )
        db.add(admin)

        profile = BarberProfile(
            tenant_id=tenant.id,
            slot_duration_minutes=defaults.slot_duration_minutes,
            work_start_time=defaults.work_start_time,
            work_end_time=defaults.work_end_time,
            weekly_closed_days=defaults.weekly_closed_days,
            max_booking_days_ahead=14,
        )
        db.add(profile)

        await _log_activity(
            db,
            super_admin=super_admin,
            action_type="tenant_created",
            tenant_id=tenant.id,
            metadata={
                "subdomain": tenant.subdomain,
                "admin_email": admin.email,
                "admin_phone": admin.phone,
                "admin_first_name": body.admin_first_name,
                "admin_last_name": body.admin_last_name,
                "parent_tenant_id": str(body.parent_tenant_id) if body.parent_tenant_id else None,
            },
        )
        await db.commit()
        await db.refresh(tenant)
        await db.refresh(admin)
    except IntegrityError as exc:
        await db.rollback()
        mapped_error = _map_integrity_error_to_http(exc)
        if mapped_error is not None:
            raise mapped_error from exc
        raise

    domain_sync = _domain_sync_response(tenant.subdomain)

    return TenantCreateResponse(
        tenant=_tenant_item(tenant, user_count=0, booking_count=0),
        admin=TenantAdminSummary(
            id=admin.id,
            email=admin.email,
            phone=admin.phone,
            created_at=admin.created_at,
        ),
        domain_sync=domain_sync,
    )


async def update_tenant(
    db: AsyncSession,
    super_admin: SuperAdmin,
    tenant_id: uuid.UUID,
    body: TenantUpdateRequest,
) -> TenantDetailResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})
    if tenant.status == TenantStatus.deleted:
        raise HTTPException(409, {"error": "tenant_deleted"})

    admin_result = await db.execute(select(Admin).where(Admin.tenant_id == tenant.id))
    admin = admin_result.scalar_one_or_none()

    if body.subdomain is not None:
        new_subdomain = _validate_subdomain(body.subdomain)
        duplicate_subdomain = await db.execute(
            select(Tenant.id).where(Tenant.subdomain == new_subdomain, Tenant.id != tenant.id)
        )
        if duplicate_subdomain.scalar_one_or_none() is not None:
            raise HTTPException(409, {"error": "subdomain_already_exists"})
        tenant.subdomain = new_subdomain

    if body.name is not None:
        tenant.name = body.name.strip()

    if body.address is not None:
        tenant.address = body.address.strip()

    body_otp_provider = getattr(body, "otp_provider", None)
    if body_otp_provider is not None:
        tenant.otp_provider = body_otp_provider

    if admin is not None and body.admin_email is not None:
        normalized_email = _normalize_email(body.admin_email)
        duplicate_email = await db.execute(
            select(Admin.id).where(Admin.email == normalized_email, Admin.id != admin.id)
        )
        if duplicate_email.scalar_one_or_none() is not None:
            raise HTTPException(409, {"error": "admin_email_already_exists"})
        admin.email = normalized_email

    if admin is not None and body.admin_phone is not None:
        new_phone = _validate_phone(body.admin_phone)
        duplicate_phone = await db.execute(
            select(Admin.id).where(Admin.phone == new_phone, Admin.id != admin.id)
        )
        if duplicate_phone.scalar_one_or_none() is not None:
            raise HTTPException(409, {"error": "admin_phone_already_exists"})
        admin.phone = new_phone

    if hasattr(body, "model_fields_set"):
        parent_field_was_sent = "parent_tenant_id" in body.model_fields_set
    else:
        parent_field_was_sent = hasattr(body, "parent_tenant_id")
    body_parent_tenant_id = getattr(body, "parent_tenant_id", None)
    if parent_field_was_sent and body_parent_tenant_id != getattr(tenant, "parent_tenant_id", None):
        await _validate_parent_tenant_assignment(db, tenant.id, body_parent_tenant_id)
        tenant.parent_tenant_id = body_parent_tenant_id

    await _log_activity(
        db,
        super_admin=super_admin,
        action_type="tenant_updated",
        tenant_id=tenant.id,
        metadata={
            "tenant_name": tenant.name,
            "subdomain": tenant.subdomain,
            "otp_provider": getattr(tenant, "otp_provider", "whatsapp"),
            "parent_tenant_id": (
                str(getattr(tenant, "parent_tenant_id", None))
                if getattr(tenant, "parent_tenant_id", None)
                else None
            ),
        },
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        mapped_error = _map_integrity_error_to_http(exc)
        if mapped_error is not None:
            raise mapped_error from exc
        raise
    return await get_tenant_detail(db, tenant.id)


async def update_tenant_whatsapp(
    db: AsyncSession,
    super_admin: SuperAdmin,
    tenant_id: uuid.UUID,
    body: TenantWhatsappUpdateRequest,
) -> TenantDetailResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})
    if tenant.status == TenantStatus.deleted:
        raise HTTPException(409, {"error": "tenant_deleted"})

    if body.phone_number_id:
        duplicate = await db.execute(
            select(Tenant.id).where(
                Tenant.whatsapp_phone_number_id == body.phone_number_id,
                Tenant.id != tenant.id,
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise HTTPException(409, {"error": "whatsapp_phone_number_id_already_exists"})

    previous_status = getattr(tenant, "whatsapp_connection_status", "disconnected")
    tenant.whatsapp_phone_number_id = body.phone_number_id
    tenant.whatsapp_waba_id = body.waba_id
    tenant.whatsapp_display_phone_number = body.display_phone_number
    tenant.whatsapp_connection_status = body.connection_status
    tenant.whatsapp_bot_enabled = body.bot_enabled
    tenant.whatsapp_bot_superadmin_enabled = body.bot_superadmin_enabled
    tenant.whatsapp_booking_enabled = body.booking_enabled
    tenant.whatsapp_booking_superadmin_enabled = body.booking_superadmin_enabled
    tenant.whatsapp_reminder_enabled = body.reminder_enabled
    tenant.whatsapp_reminder_superadmin_enabled = body.reminder_superadmin_enabled
    tenant.whatsapp_cancellation_enabled = body.cancellation_enabled
    tenant.whatsapp_cancellation_superadmin_enabled = body.cancellation_superadmin_enabled
    tenant.whatsapp_reschedule_enabled = body.reschedule_enabled
    tenant.whatsapp_reschedule_superadmin_enabled = body.reschedule_superadmin_enabled
    tenant.whatsapp_long_absence_enabled = body.long_absence_enabled
    tenant.whatsapp_long_absence_superadmin_enabled = body.long_absence_superadmin_enabled
    tenant.whatsapp_long_absence_days = body.long_absence_days
    tenant.whatsapp_silent_numbers = normalize_silent_numbers(body.silent_numbers)
    if body.connection_status == "connected" and previous_status != "connected":
        tenant.whatsapp_connected_at = datetime.now(timezone.utc)
    if body.connection_status != "connected":
        tenant.whatsapp_connected_at = None

    await _log_activity(
        db,
        super_admin=super_admin,
        action_type="tenant_whatsapp_updated",
        tenant_id=tenant.id,
        metadata={
            "phone_number_id": tenant.whatsapp_phone_number_id,
            "waba_id": tenant.whatsapp_waba_id,
            "connection_status": tenant.whatsapp_connection_status,
            "bot_enabled": tenant.whatsapp_bot_enabled,
            "bot_superadmin_enabled": tenant.whatsapp_bot_superadmin_enabled,
            "booking_enabled": tenant.whatsapp_booking_enabled,
            "booking_superadmin_enabled": tenant.whatsapp_booking_superadmin_enabled,
            "reminder_enabled": tenant.whatsapp_reminder_enabled,
            "reminder_superadmin_enabled": tenant.whatsapp_reminder_superadmin_enabled,
            "cancellation_enabled": tenant.whatsapp_cancellation_enabled,
            "cancellation_superadmin_enabled": tenant.whatsapp_cancellation_superadmin_enabled,
            "reschedule_enabled": tenant.whatsapp_reschedule_enabled,
            "reschedule_superadmin_enabled": tenant.whatsapp_reschedule_superadmin_enabled,
            "long_absence_enabled": tenant.whatsapp_long_absence_enabled,
            "long_absence_superadmin_enabled": tenant.whatsapp_long_absence_superadmin_enabled,
            "long_absence_days": tenant.whatsapp_long_absence_days,
            "silent_numbers_count": len(tenant.whatsapp_silent_numbers or []),
        },
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        message = str(exc.orig).lower() if getattr(exc, "orig", None) else str(exc).lower()
        if "whatsapp_phone_number_id" in message:
            raise HTTPException(409, {"error": "whatsapp_phone_number_id_already_exists"}) from exc
        raise
    return await get_tenant_detail(db, tenant.id)


async def update_tenant_status(
    db: AsyncSession,
    super_admin: SuperAdmin,
    tenant_id: uuid.UUID,
    body: TenantStatusUpdateRequest,
) -> TenantStatusUpdateResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})
    if tenant.status == TenantStatus.deleted:
        raise HTTPException(409, {"error": "tenant_deleted"})

    next_status = TenantStatus.active if body.status == "active" else TenantStatus.inactive
    tenant.status = next_status
    tenant.is_active = next_status == TenantStatus.active
    await _log_activity(
        db,
        super_admin=super_admin,
        action_type="tenant_status_changed",
        tenant_id=tenant.id,
        metadata={"status": tenant.status.value, "reason": body.reason},
    )
    await db.commit()
    return TenantStatusUpdateResponse(id=tenant.id, status=tenant.status, is_active=tenant.is_active)


async def soft_delete_tenant(
    db: AsyncSession,
    super_admin: SuperAdmin,
    tenant_id: uuid.UUID,
) -> TenantStatusUpdateResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})

    if tenant.status != TenantStatus.deleted:
        tenant.status = TenantStatus.deleted
        tenant.is_active = False
        await _log_activity(
            db,
            super_admin=super_admin,
            action_type="tenant_deleted",
            tenant_id=tenant.id,
            metadata={"status": "deleted"},
        )
        await db.commit()

    return TenantStatusUpdateResponse(id=tenant.id, status=tenant.status, is_active=tenant.is_active)


async def hard_delete_tenant(
    db: AsyncSession,
    super_admin: SuperAdmin,
    tenant_id: uuid.UUID,
) -> TenantHardDeleteResponse:
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})

    await db.execute(delete(Booking).where(Booking.tenant_id == tenant.id))
    await db.execute(delete(OTPRecord).where(OTPRecord.tenant_id == tenant.id))
    await db.execute(delete(SlotBlock).where(SlotBlock.tenant_id == tenant.id))
    await db.execute(delete(DayOverride).where(DayOverride.tenant_id == tenant.id))
    await db.execute(delete(WaContactLog).where(WaContactLog.tenant_id == tenant.id))
    await db.execute(delete(WaErrorLog).where(WaErrorLog.tenant_id == tenant.id))
    await db.execute(delete(ErrorLog).where(ErrorLog.tenant_id == tenant.id))
    await db.execute(delete(ActivityLog).where(ActivityLog.tenant_id == tenant.id))
    await db.execute(delete(User).where(User.tenant_id == tenant.id))
    await db.execute(delete(Admin).where(Admin.tenant_id == tenant.id))
    await db.execute(delete(BarberProfile).where(BarberProfile.tenant_id == tenant.id))
    await db.execute(delete(Tenant).where(Tenant.id == tenant.id))

    db.add(
        ActivityLog(
            super_admin_id=super_admin.id,
            action_type="tenant_hard_deleted",
            entity_type="tenant",
            entity_id=str(tenant.id),
            tenant_id=None,
            metadata_json=None,
        )
    )
    await db.commit()
    return TenantHardDeleteResponse(id=tenant.id, message="tenant_hard_deleted")
