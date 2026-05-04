"""superadmin/whatsapp_service.py — WhatsApp bot istatistik ve hata servisleri."""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.booking import Booking
from app.models.tenant import Tenant
from app.models.wa_contact_log import WaContactLog
from app.models.wa_error_log import WaErrorLog
from app.modules.superadmin.whatsapp_schemas import (
    PaginationMeta,
    WaBookingStats,
    WaContactStats,
    WaErrorLogItem,
    WaErrorLogListResponse,
    WaHealthResponse,
    WaStatsResponse,
    WaTenantBreakdown,
)

TZ = ZoneInfo("Europe/Istanbul")


def _local_today() -> date:
    return datetime.now(TZ).date()


def _week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def _month_start(today: date) -> date:
    return today.replace(day=1)


def _booking_window(start: date) -> datetime:
    return datetime.combine(start, datetime.min.time(), tzinfo=TZ)


async def get_wa_health(db: AsyncSession) -> WaHealthResponse:
    settings = get_settings()
    token_configured = bool(settings.wa_access_token)
    pid_configured = bool(settings.wa_phone_number_id)

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    count_result = await db.execute(
        select(func.count(WaErrorLog.id)).where(WaErrorLog.created_at >= since)
    )
    errors_24h = int(count_result.scalar_one() or 0)

    last_result = await db.execute(
        select(WaErrorLog.created_at).order_by(WaErrorLog.created_at.desc()).limit(1)
    )
    last_error_at = last_result.scalar_one_or_none()

    return WaHealthResponse(
        token_configured=token_configured,
        phone_number_id_configured=pid_configured,
        errors_last_24h=errors_24h,
        last_error_at=last_error_at,
    )


async def get_wa_stats(db: AsyncSession) -> WaStatsResponse:
    today = _local_today()
    week_start = _week_start(today)
    month_start = _month_start(today)

    # ── Benzersiz temas sayıları ──────────────────────────────────────────────
    async def _unique_contacts(from_date: date, to_date: date | None = None) -> int:
        stmt = select(func.count(func.distinct(WaContactLog.wa_phone))).where(
            WaContactLog.contact_date >= from_date
        )
        if to_date:
            stmt = stmt.where(WaContactLog.contact_date <= to_date)
        result = await db.execute(stmt)
        return int(result.scalar_one() or 0)

    unique_today = await _unique_contacts(today, today)
    unique_week = await _unique_contacts(week_start)
    unique_month = await _unique_contacts(month_start)

    # ── Randevu kaynak dağılımı ───────────────────────────────────────────────
    async def _booking_count(source: str, from_dt: datetime) -> int:
        result = await db.execute(
            select(func.count(Booking.id)).where(
                Booking.source == source,
                Booking.created_at >= from_dt,
            )
        )
        return int(result.scalar_one() or 0)

    today_dt = _booking_window(today)
    week_dt = _booking_window(week_start)
    month_dt = _booking_window(month_start)

    wa_today = await _booking_count("whatsapp", today_dt)
    wa_week = await _booking_count("whatsapp", week_dt)
    wa_month = await _booking_count("whatsapp", month_dt)
    web_today = await _booking_count("web", today_dt)
    web_week = await _booking_count("web", week_dt)
    web_month = await _booking_count("web", month_dt)

    # ── Tenant bazlı bu ay dağılımı ───────────────────────────────────────────
    tenants_result = await db.execute(
        select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.name)
    )
    tenants = list(tenants_result.scalars().all())

    breakdown: list[WaTenantBreakdown] = []
    for t in tenants:
        fn = (t.first_name or "").strip()
        ln = (t.last_name or "").strip()
        display = f"{fn} {ln}".strip() if fn or ln else t.name

        wa_res = await db.execute(
            select(func.count(Booking.id)).where(
                Booking.tenant_id == t.id,
                Booking.source == "whatsapp",
                Booking.created_at >= month_dt,
            )
        )
        wa_cnt = int(wa_res.scalar_one() or 0)

        web_res = await db.execute(
            select(func.count(Booking.id)).where(
                Booking.tenant_id == t.id,
                Booking.source == "web",
                Booking.created_at >= month_dt,
            )
        )
        web_cnt = int(web_res.scalar_one() or 0)

        if wa_cnt > 0 or web_cnt > 0:
            breakdown.append(
                WaTenantBreakdown(
                    tenant_id=t.id,
                    tenant_name=display,
                    wa_bookings_month=wa_cnt,
                    web_bookings_month=web_cnt,
                    total_bookings_month=wa_cnt + web_cnt,
                )
            )

    breakdown.sort(key=lambda x: x.total_bookings_month, reverse=True)

    return WaStatsResponse(
        unique_contacts=WaContactStats(
            today=unique_today,
            this_week=unique_week,
            this_month=unique_month,
        ),
        bookings=WaBookingStats(
            wa_today=wa_today,
            wa_week=wa_week,
            wa_month=wa_month,
            web_today=web_today,
            web_week=web_week,
            web_month=web_month,
        ),
        tenant_breakdown=breakdown,
    )


async def list_wa_errors(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    tenant_id: uuid.UUID | None,
    error_type: str | None,
    q: str | None,
) -> WaErrorLogListResponse:
    filters = []
    if tenant_id:
        filters.append(WaErrorLog.tenant_id == tenant_id)
    if error_type:
        filters.append(WaErrorLog.error_type == error_type)
    if q and q.strip():
        qv = f"%{q.strip()}%"
        filters.append(
            or_(WaErrorLog.message.ilike(qv), WaErrorLog.wa_phone.ilike(qv))
        )

    base = select(WaErrorLog)
    count_stmt = select(func.count(WaErrorLog.id))
    if filters:
        base = base.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    total_pages = math.ceil(total / page_size) if total else 0

    rows = (
        await db.execute(
            base.order_by(WaErrorLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return WaErrorLogListResponse(
        items=[
            WaErrorLogItem(
                id=r.id,
                tenant_id=r.tenant_id,
                wa_phone=r.wa_phone,
                error_type=r.error_type,
                message=r.message,
                meta_json=r.meta_json,
                created_at=r.created_at,
            )
            for r in rows
        ],
        pagination=PaginationMeta(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        ),
    )
