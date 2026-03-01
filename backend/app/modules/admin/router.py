"""
admin/router.py — Admin panel HTTP endpoint'leri.

Bu dosya sadece HTTP katmanıdır:
- Request'i alır, parametreleri doğrular
- Service fonksiyonunu çağırır
- Response'u döndürür

Business logic admin/service.py içindedir.

Endpoint'ler:
  GET /admin/dashboard?date=YYYY-MM-DD  — Günlük özet: tıraş sayısı + randevu listesi
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.admin import Admin
from app.modules.admin import service as admin_service
from app.modules.admin.schemas import DashboardResponse

# prefix="/admin" — tüm bu router'ın endpoint'leri /api/v1/admin/ ile başlar
router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    date: date = Query(..., description="Tarih: YYYY-MM-DD formatında — örn: 2026-02-25"),
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin için günlük özet dashboard.

    Döndürdükleri:
    - confirmed_count: O gün status='confirmed' olan randevu sayısı
      (Günlük tıraş sayısı — cancelled randevular bu sayıya dahil değil)
    - bookings: O günün tüm randevuları (confirmed + cancelled), slot_time ASC sıralı
      Her randevuda müşteri adı, soyadı ve telefonu vardır.

    Para bilgisi yoktur (CLAUDE.md: ödeme MVP dışı).
    """
    # admin.tenant_id: middleware'den gelen tenant — başka berber'in verisi okunamaz
    data = await admin_service.get_dashboard(
        db,
        tenant_id=admin.tenant_id,
        target_date=date,
    )
    return DashboardResponse(**data)
