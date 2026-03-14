"""
admin/router.py - Admin panel HTTP endpoint'leri.

Bu dosya sadece HTTP katmanidir:
- Request'i alir, parametreleri dogrular
- Service fonksiyonunu cagirir
- Response'u dondurur

Business logic admin/service.py icindedir.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.admin import Admin
from app.modules.admin import service as admin_service
from app.modules.admin.schemas import (
    AdminOverviewResponse,
    AdminStatisticsResponse,
    DashboardResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    date: date = Query(..., description="Tarih: YYYY-MM-DD formatinda - orn: 2026-02-25"),
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin icin gunluk ozet dashboard.

    Bu endpoint geriye donuk uyumluluk icin korunur.
    """
    data = await admin_service.get_dashboard(
        db,
        tenant_id=admin.tenant_id,
        target_date=date,
    )
    return DashboardResponse(**data)


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_overview(
    date: date = Query(..., description="Tarih: YYYY-MM-DD formatinda - orn: 2026-02-25"),
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin icin birlesik panel verisi.

    Tek cagriyla su alanlari dondurur:
    - bookings (dashboard listesi)
    - slots (gunluk slot listesi)
    - blocks (bloklu slotlar)
    """
    data = await admin_service.get_overview(
        db,
        tenant_id=admin.tenant_id,
        target_date=date,
    )
    return AdminOverviewResponse(**data)


@router.get("/statistics", response_model=AdminStatisticsResponse)
async def get_statistics(
    date: date = Query(..., description="Tarih: YYYY-MM-DD formatinda - orn: 2026-02-25"),
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin icin gunluk, haftalik ve aylik istatistik verileri.
    """
    data = await admin_service.get_statistics(
        db,
        tenant_id=admin.tenant_id,
        target_date=date,
    )
    return AdminStatisticsResponse(**data)
