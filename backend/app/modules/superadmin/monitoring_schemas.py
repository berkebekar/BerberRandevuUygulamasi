"""
superadmin/monitoring_schemas.py - Monitoring ve log endpoint schema'lari.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ServiceHealthItem(BaseModel):
    name: str
    status: str
    response_ms: float | None = None
    last_checked_at: datetime | None = None
    meta: dict | None = None


class HostResourceUsage(BaseModel):
    cpu_percent: float | None = None
    ram_percent: float | None = None
    disk_percent: float | None = None
    ram_used_mb: float | None = None
    ram_total_mb: float | None = None
    disk_used_gb: float | None = None
    disk_total_gb: float | None = None


class MonitoringHealthResponse(BaseModel):
    checked_at: datetime
    services: list[ServiceHealthItem]
    host_resources: HostResourceUsage | None = None


class UptimeSummaryItem(BaseModel):
    service: str
    uptime_percent: float
    checks_total: int
    checks_up: int


class UptimeSeriesPoint(BaseModel):
    ts: datetime
    status: str
    response_ms: int | None = None


class UptimeSeriesItem(BaseModel):
    service: str
    points: list[UptimeSeriesPoint]


class MonitoringUptimeResponse(BaseModel):
    window_hours: int
    checked_at: datetime
    summary: list[UptimeSummaryItem]
    series: list[UptimeSeriesItem]


class ErrorLogListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    request_id: str | None = None
    endpoint: str
    method: str
    status_code: int
    error_code: str | None = None
    message: str
    created_at: datetime


class ErrorLogListResponse(BaseModel):
    items: list[ErrorLogListItem]
    pagination: PaginationMeta


class ErrorLogDetailResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    request_id: str | None = None
    endpoint: str
    method: str
    status_code: int
    error_code: str | None = None
    message: str
    stack_trace: str | None = None
    request_meta: dict | None = None
    created_at: datetime


class ActivityLogItem(BaseModel):
    id: uuid.UUID
    super_admin_id: uuid.UUID | None = None
    action_type: str
    entity_type: str
    entity_id: str | None = None
    tenant_id: uuid.UUID | None = None
    metadata_json: dict | None = None
    created_at: datetime


class ActivityLogListResponse(BaseModel):
    items: list[ActivityLogItem]
    pagination: PaginationMeta
