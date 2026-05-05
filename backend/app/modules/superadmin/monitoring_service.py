"""
superadmin/monitoring_service.py - Monitoring ve logging endpoint servisleri.
"""

from __future__ import annotations

import asyncio
import math
import shutil
import time
import uuid
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.activity_log import ActivityLog
from app.models.error_log import ErrorLog
from app.models.uptime_check import UptimeCheck
from app.modules.superadmin.monitoring_schemas import (
    ActivityLogItem,
    ActivityLogListResponse,
    ErrorLogDetailResponse,
    ErrorLogListItem,
    ErrorLogListResponse,
    HostResourceUsage,
    MonitoringHealthResponse,
    MonitoringUptimeResponse,
    PaginationMeta,
    ServiceHealthItem,
    UptimeSeriesItem,
    UptimeSeriesPoint,
    UptimeSummaryItem,
)

_CPU_SAMPLE_DELAY_SECONDS = 0.12


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


def _read_cpu_times_linux() -> tuple[int, int] | None:
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            line = f.readline().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None
    parts = line.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return None
    try:
        values = [int(v) for v in parts[1:]]
    except ValueError:
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return total, idle


async def _measure_cpu_percent_linux() -> float | None:
    first = _read_cpu_times_linux()
    if first is None:
        return None
    await asyncio.sleep(_CPU_SAMPLE_DELAY_SECONDS)
    second = _read_cpu_times_linux()
    if second is None:
        return None
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    busy_ratio = 1 - (idle_delta / total_delta)
    return round(max(0.0, min(100.0, busy_ratio * 100)), 2)


def _read_ram_usage_linux() -> tuple[float, float, float] | None:
    mem_total_kb: int | None = None
    mem_available_kb: int | None = None
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available_kb = int(line.split()[1])
                if mem_total_kb is not None and mem_available_kb is not None:
                    break
    except (FileNotFoundError, PermissionError, OSError, ValueError):
        return None
    if not mem_total_kb or mem_available_kb is None or mem_total_kb <= 0:
        return None
    used_kb = max(0, mem_total_kb - mem_available_kb)
    percent = round((used_kb / mem_total_kb) * 100, 2)
    return (
        percent,
        round(used_kb / 1024, 2),
        round(mem_total_kb / 1024, 2),
    )


def _read_disk_usage(path: str = "/") -> tuple[float, float, float] | None:
    try:
        disk = shutil.disk_usage(path)
    except (FileNotFoundError, PermissionError, OSError):
        return None
    if disk.total <= 0:
        return None
    percent = round((disk.used / disk.total) * 100, 2)
    used_gb = round(disk.used / (1024 ** 3), 2)
    total_gb = round(disk.total / (1024 ** 3), 2)
    return percent, used_gb, total_gb


def _resolve_frontend_health_url() -> str:
    settings = get_settings()
    raw = (settings.frontend_healthcheck_url or "").strip()
    if raw:
        return raw
    app_domain = (settings.app_domain or "").strip()
    allowed_subdomains = [s.strip() for s in (settings.allowed_subdomains or "").split(",") if s.strip()]
    if app_domain and allowed_subdomains:
        return f"https://{allowed_subdomains[0]}.{app_domain}"
    return "http://localhost:3000"


async def _check_frontend_health() -> tuple[str, float | None, datetime, dict | None]:
    checked_at = datetime.now(timezone.utc)
    url = _resolve_frontend_health_url()
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            response = await client.get(url)
        response_ms = round((time.perf_counter() - started) * 1000, 2)
        status = "operational" if 200 <= response.status_code < 400 else "down"
        meta = {"url": url, "http_status": response.status_code}
        return status, response_ms, checked_at, meta
    except Exception as exc:
        meta = {"url": url, "error": str(exc)}
        return "unknown", None, checked_at, meta


async def _collect_host_resources() -> HostResourceUsage:
    cpu_percent = await _measure_cpu_percent_linux()
    ram = _read_ram_usage_linux()
    disk = _read_disk_usage("/")
    return HostResourceUsage(
        cpu_percent=cpu_percent,
        ram_percent=ram[0] if ram else None,
        disk_percent=disk[0] if disk else None,
        ram_used_mb=ram[1] if ram else None,
        ram_total_mb=ram[2] if ram else None,
        disk_used_gb=disk[1] if disk else None,
        disk_total_gb=disk[2] if disk else None,
    )


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

    frontend_status, frontend_response_ms, frontend_checked_at, frontend_meta = await _check_frontend_health()
    host_resources = await _collect_host_resources()

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
                response_ms=frontend_response_ms,
                last_checked_at=frontend_checked_at,
                meta=frontend_meta,
            ),
        ],
        host_resources=host_resources,
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
