"""
superadmin/monitoring_service.py - Monitoring ve logging endpoint servisleri.
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.error_log import ErrorLog
from app.models.uptime_check import UptimeCheck
from app.modules.superadmin.monitoring_schemas import (
    ActivityLogItem,
    ActivityLogListResponse,
    ErrorLogDetailResponse,
    ErrorLogListItem,
    ErrorLogListResponse,
    MonitoringHealthResponse,
    MonitoringUptimeResponse,
    PaginationMeta,
    ServiceHealthItem,
    UptimeSeriesItem,
    UptimeSeriesPoint,
    UptimeSummaryItem,
)


def _window_bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    start = datetime.combine(date_from, dt_time.min, tzinfo=timezone.utc) if date_from else None
    end = datetime.combine(date_to, dt_time.max, tzinfo=timezone.utc) if date_to else None
    return start, end


def _is_up_status(status: str) -> bool:
    normalized = (status or "").strip().lower()
    return normalized in {"up", "ok", "operational", "healthy"}


def _safe_meta(meta: dict | None) -> dict | None:
    if not isinstance(meta, dict):
        return meta
    clean = dict(meta)
    headers = clean.get("headers")
    if isinstance(headers, dict):
        for key in list(headers.keys()):
            lowered = key.lower()
            if lowered in {"authorization", "cookie", "set-cookie", "x-api-key"}:
                headers[key] = "***"
    body = clean.get("body")
    if isinstance(body, dict):
        for key in list(body.keys()):
            if any(token in key.lower() for token in {"password", "token", "code", "otp", "secret"}):
                body[key] = "***"
    return clean


async def get_monitoring_health(db: AsyncSession) -> MonitoringHealthResponse:
    checked_at = datetime.now(timezone.utc)
    backend_started = time.perf_counter()
    backend_ms = (time.perf_counter() - backend_started) * 1000

    db_started = time.perf_counter()
    db_status = "operational"
    db_meta: dict | None = None
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "down"
        db_meta = {"error": str(exc)}
    db_ms = (time.perf_counter() - db_started) * 1000

    frontend_result = await db.execute(
        select(UptimeCheck)
        .where(UptimeCheck.service_name == "frontend")
        .order_by(UptimeCheck.checked_at.desc())
        .limit(1)
    )
    frontend_last = frontend_result.scalar_one_or_none()
    frontend_status = frontend_last.status if frontend_last else "unknown"

    return MonitoringHealthResponse(
        checked_at=checked_at,
        services=[
            ServiceHealthItem(
                name="backend",
                status="operational",
                response_ms=round(backend_ms, 2),
                last_checked_at=checked_at,
                meta=None,
            ),
            ServiceHealthItem(
                name="database",
                status=db_status,
                response_ms=round(db_ms, 2),
                last_checked_at=checked_at,
                meta=db_meta,
            ),
            ServiceHealthItem(
                name="frontend",
                status=frontend_status,
                response_ms=frontend_last.response_ms if frontend_last else None,
                last_checked_at=frontend_last.checked_at if frontend_last else None,
                meta=frontend_last.meta_json if frontend_last else None,
            ),
        ],
    )


async def get_monitoring_uptime(db: AsyncSession) -> MonitoringUptimeResponse:
    checked_at = datetime.now(timezone.utc)
    since_24h = checked_at - timedelta(hours=24)
    result = await db.execute(
        select(UptimeCheck)
        .where(UptimeCheck.checked_at >= since_24h)
        .order_by(UptimeCheck.service_name.asc(), UptimeCheck.checked_at.asc())
    )
    checks = list(result.scalars().all())

    grouped: dict[str, list[UptimeCheck]] = defaultdict(list)
    for check in checks:
        grouped[check.service_name].append(check)

    summary: list[UptimeSummaryItem] = []
    series: list[UptimeSeriesItem] = []
    for service_name, items in grouped.items():
        total = len(items)
        checks_up = sum(1 for item in items if _is_up_status(item.status))
        uptime_percent = round((checks_up / total) * 100, 2) if total else 0.0
        summary.append(
            UptimeSummaryItem(
                service=service_name,
                uptime_percent=uptime_percent,
                checks_total=total,
                checks_up=checks_up,
            )
        )
        series.append(
            UptimeSeriesItem(
                service=service_name,
                points=[
                    UptimeSeriesPoint(ts=item.checked_at, status=item.status, response_ms=item.response_ms)
                    for item in items
                ],
            )
        )

    summary.sort(key=lambda item: item.service)
    series.sort(key=lambda item: item.service)
    return MonitoringUptimeResponse(window_hours=24, checked_at=checked_at, summary=summary, series=series)


async def list_error_logs(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    tenant_id: uuid.UUID | None,
    endpoint: str | None,
    status_code: int | None,
    date_from: date | None,
    date_to: date | None,
    error_code: str | None,
    q: str | None,
) -> ErrorLogListResponse:
    filters = []
    if tenant_id:
        filters.append(ErrorLog.tenant_id == tenant_id)
    if endpoint:
        filters.append(ErrorLog.endpoint.ilike(f"%{endpoint.strip()}%"))
    if status_code is not None:
        filters.append(ErrorLog.status_code == status_code)
    if error_code:
        filters.append(ErrorLog.error_code == error_code)
    start_dt, end_dt = _window_bounds(date_from, date_to)
    if start_dt:
        filters.append(ErrorLog.created_at >= start_dt)
    if end_dt:
        filters.append(ErrorLog.created_at <= end_dt)
    if q and q.strip():
        qv = f"%{q.strip()}%"
        filters.append(or_(ErrorLog.message.ilike(qv), ErrorLog.endpoint.ilike(qv)))

    total_stmt = select(func.count(ErrorLog.id))
    if filters:
        total_stmt = total_stmt.where(and_(*filters))
    total_result = await db.execute(total_stmt)
    total = int(total_result.scalar_one() or 0)
    total_pages = math.ceil(total / page_size) if total else 0

    list_stmt = select(ErrorLog)
    if filters:
        list_stmt = list_stmt.where(and_(*filters))
    list_result = await db.execute(
        list_stmt.order_by(ErrorLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        ErrorLogListItem(
            id=item.id,
            tenant_id=item.tenant_id,
            request_id=item.request_id,
            endpoint=item.endpoint,
            method=item.method,
            status_code=item.status_code,
            error_code=item.error_code,
            message=item.message,
            created_at=item.created_at,
        )
        for item in list_result.scalars().all()
    ]
    return ErrorLogListResponse(
        items=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


async def get_error_log_detail(db: AsyncSession, error_id: uuid.UUID) -> ErrorLogDetailResponse:
    result = await db.execute(select(ErrorLog).where(ErrorLog.id == error_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(404, {"error": "error_log_not_found"})
    return ErrorLogDetailResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        request_id=item.request_id,
        endpoint=item.endpoint,
        method=item.method,
        status_code=item.status_code,
        error_code=item.error_code,
        message=item.message,
        stack_trace=item.stack_trace,
        request_meta=_safe_meta(item.request_meta_json),
        created_at=item.created_at,
    )


async def list_activity_logs(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    action_type: str | None,
    tenant_id: uuid.UUID | None,
    super_admin_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
) -> ActivityLogListResponse:
    filters = []
    if action_type:
        filters.append(ActivityLog.action_type == action_type)
    if tenant_id:
        filters.append(ActivityLog.tenant_id == tenant_id)
    if super_admin_id:
        filters.append(ActivityLog.super_admin_id == super_admin_id)
    start_dt, end_dt = _window_bounds(date_from, date_to)
    if start_dt:
        filters.append(ActivityLog.created_at >= start_dt)
    if end_dt:
        filters.append(ActivityLog.created_at <= end_dt)

    total_stmt = select(func.count(ActivityLog.id))
    if filters:
        total_stmt = total_stmt.where(and_(*filters))
    total_result = await db.execute(total_stmt)
    total = int(total_result.scalar_one() or 0)
    total_pages = math.ceil(total / page_size) if total else 0

    list_stmt = select(ActivityLog)
    if filters:
        list_stmt = list_stmt.where(and_(*filters))
    list_result = await db.execute(
        list_stmt.order_by(ActivityLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    items = [
        ActivityLogItem(
            id=item.id,
            super_admin_id=item.super_admin_id,
            action_type=item.action_type,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            tenant_id=item.tenant_id,
            metadata_json=item.metadata_json,
            created_at=item.created_at,
        )
        for item in list_result.scalars().all()
    ]
    return ActivityLogListResponse(
        items=items,
        pagination=PaginationMeta(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )
