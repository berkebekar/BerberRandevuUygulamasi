"""
superadmin/stats.py - Super admin dashboard stats endpoint'leri.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.modules.superadmin.stats_schemas import (
    SuperAdminOverviewResponse,
    SuperAdminRecentActivitiesResponse,
    SuperAdminTrendsResponse,
)
from app.modules.superadmin.stats_service import (
    get_overview_stats,
    get_recent_activities,
    get_trends_stats,
)

router = APIRouter(
    prefix="/superadmin/stats",
    tags=["superadmin-stats"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("/overview", response_model=SuperAdminOverviewResponse, status_code=200)
async def super_admin_stats_overview(
    db: AsyncSession = Depends(get_db),
):
    return await get_overview_stats(db)


@router.get("/trends", response_model=SuperAdminTrendsResponse, status_code=200)
async def super_admin_stats_trends(
    db: AsyncSession = Depends(get_db),
):
    return await get_trends_stats(db)


@router.get("/recent-activities", response_model=SuperAdminRecentActivitiesResponse, status_code=200)
async def super_admin_stats_recent_activities(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_recent_activities(db, limit=limit)

