"""superadmin/bookings_service.py — Tüm tenant randevularını listeler."""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.superadmin.bookings_schemas import (
    BookingListItem,
    BookingListResponse,
)
from app.modules.superadmin.monitoring_schemas import PaginationMeta

TZ = ZoneInfo("Europe/Istanbul")


async def list_bookings(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    tenant_id: uuid.UUID | None,
    status: str | None,
    source: str | None,
    date_from: date | None,
    date_to: date | None,
    q: str | None,
) -> BookingListResponse:
    filters = []

    if tenant_id:
        filters.append(Booking.tenant_id == tenant_id)
    if status:
        filters.append(Booking.status == status)
    if source:
        filters.append(Booking.source == source)
    if date_from:
        dt_from = datetime.combine(date_from, datetime.min.time(), tzinfo=TZ)
        filters.append(Booking.slot_time >= dt_from)
    if date_to:
        dt_to = datetime.combine(date_to, datetime.max.time(), tzinfo=TZ)
        filters.append(Booking.slot_time <= dt_to)
    if q and q.strip():
        qv = f"%{q.strip()}%"
        filters.append(
            or_(
                User.first_name.ilike(qv),
                User.last_name.ilike(qv),
                User.phone.ilike(qv),
                (User.first_name + " " + User.last_name).ilike(qv),
            )
        )

    base_stmt = (
        select(Booking, User, Tenant)
        .join(User, User.id == Booking.user_id)
        .join(Tenant, Tenant.id == Booking.tenant_id)
    )
    count_stmt = (
        select(func.count(Booking.id))
        .join(User, User.id == Booking.user_id)
        .join(Tenant, Tenant.id == Booking.tenant_id)
    )

    if filters:
        base_stmt = base_stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    total_pages = math.ceil(total / page_size) if total else 0

    rows = (
        await db.execute(
            base_stmt.order_by(Booking.created_at.desc(), Booking.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    items: list[BookingListItem] = []
    for booking, user, tenant in rows:
        fn = (user.first_name or "").strip()
        ln = (user.last_name or "").strip()
        customer_name = f"{fn} {ln}".strip() if fn or ln else user.phone

        tn = (tenant.first_name or "").strip()
        tln = (tenant.last_name or "").strip()
        tenant_name = f"{tn} {tln}".strip() if tn or tln else tenant.name

        items.append(
            BookingListItem(
                id=booking.id,
                tenant_id=booking.tenant_id,
                tenant_name=tenant_name,
                user_id=booking.user_id,
                customer_name=customer_name,
                customer_phone=user.phone,
                slot_time=booking.slot_time,
                status=booking.status.value if hasattr(booking.status, "value") else str(booking.status),
                cancelled_by=booking.cancelled_by.value if booking.cancelled_by and hasattr(booking.cancelled_by, "value") else (str(booking.cancelled_by) if booking.cancelled_by else None),
                source=booking.source,
                created_at=booking.created_at,
            )
        )

    return BookingListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )
