"""
superadmin/monitoring.py - Monitoring ve log endpoint'leri.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.modules.superadmin.monitoring_schemas import (
    ActivityLogListResponse,
    ErrorLogDetailResponse,
    ErrorLogListResponse,
    MonitoringHealthResponse,
    MonitoringUptimeResponse,
)
from app.modules.superadmin.monitoring_service import (
    get_error_log_detail,
    get_monitoring_health,
    get_monitoring_uptime,
    list_activity_logs,
    list_error_logs,
)

router = APIRouter(
    prefix="/superadmin",
    tags=["superadmin-monitoring"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("/monitoring/health", response_model=MonitoringHealthResponse, status_code=200)
async def super_admin_monitoring_health(
    db: AsyncSession = Depends(get_db),
):
    return await get_monitoring_health(db)


@router.get("/monitoring/uptime", response_model=MonitoringUptimeResponse, status_code=200)
async def super_admin_monitoring_uptime(
    db: AsyncSession = Depends(get_db),
):
    return await get_monitoring_uptime(db)


@router.get("/logs/errors", response_model=ErrorLogListResponse, status_code=200)
async def super_admin_list_error_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    endpoint: str | None = Query(None),
    status_code: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    error_code: str | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_error_logs(
        db,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        endpoint=endpoint,
        status_code=status_code,
        date_from=date_from,
        date_to=date_to,
        error_code=error_code,
        q=q,
    )


@router.get("/logs/errors/{error_id}", response_model=ErrorLogDetailResponse, status_code=200)
async def super_admin_get_error_log_detail(
    error_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await get_error_log_detail(db, error_id)


@router.get("/logs/activities", response_model=ActivityLogListResponse, status_code=200)
async def super_admin_list_activity_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    action_type: str | None = Query(None),
    tenant_id: uuid.UUID | None = Query(None),
    super_admin_id: uuid.UUID | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_activity_logs(
        db,
        page=page,
        page_size=page_size,
        action_type=action_type,
        tenant_id=tenant_id,
        super_admin_id=super_admin_id,
        date_from=date_from,
        date_to=date_to,
    )
