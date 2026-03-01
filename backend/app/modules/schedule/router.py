"""
schedule/router.py — Slot ve çizelge yönetimi endpoint'leri.

Public (tenant gerektirir, auth gerekmez):
  GET  /slots?date=YYYY-MM-DD             → Günlük slot listesi
  GET  /slots/week?start=YYYY-MM-DD       → 7 günlük slot listesi

Admin (admin_session cookie gerektirir):
  GET  /admin/schedule/settings           → Çalışma saatlerini oku
  PUT  /admin/schedule/settings           → Çalışma saatlerini güncelle
  POST /admin/schedule/override           → Belirli gün için override ekle
  POST /admin/slots/block                 → Slotu kapat
  DELETE /admin/slots/block/{block_id}    → Slotu aç

Business logic schedule/service.py içindedir.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_tenant_id
from app.models.admin import Admin
from app.modules.schedule import service as schedule_service
from app.modules.schedule.schemas import (
    BarberSettingsRequest,
    BarberSettingsResponse,
    BlockSlotRequest,
    BlockSlotResponse,
    BlockedSlotItem,
    BlockedSlotsResponse,
    DayOverrideRequest,
    DaySlots,
    WeekSlots,
)

# Prefix yok — endpoint path'leri dekoratörde tam olarak belirtiliyor.
# Çünkü slot endpoint'leri (/slots) ile admin endpoint'leri (/admin/...)
# ortak bir prefix paylaşmıyor.
router = APIRouter(tags=["schedule"])


# ─── Public: Slot Okuma ───────────────────────────────────────────────────────

@router.get("/slots", response_model=DaySlots)
async def get_slots(
    date: date = Query(..., description="Tarih: YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Belirli bir güne ait slot listesini döndürür.

    Her slot için status:
    - available: rezerve edilebilir
    - booked: dolu
    - blocked: admin kapattı
    - past: zaman geçti

    Hem müşteri hem admin bu endpoint'i kullanır.
    """
    return await schedule_service.get_slots_for_date(db, tenant_id, date)


@router.get("/slots/week", response_model=WeekSlots)
async def get_slots_week(
    start: date = Query(..., description="Haftanın başlangıç tarihi: YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    start tarihinden itibaren 7 günlük slot listesi döndürür.

    Performans: 7 günün booking ve block verileri tek sorguda çekilir.
    Müşteri takvim görünümü ve admin haftalık plan için kullanılır.
    """
    return await schedule_service.get_slots_for_week(db, tenant_id, start)


# ─── Admin: Berber Ayarları ───────────────────────────────────────────────────

@router.get("/admin/schedule/settings", response_model=BarberSettingsResponse | None)
async def get_schedule_settings(
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Berberin çalışma saatlerini ve slot süresini döndürür.
    Henüz ayar girilmemişse null döner.
    """
    profile = await schedule_service.get_barber_settings(db, admin.tenant_id)
    if profile is None:
        return None
    return BarberSettingsResponse(
        slot_duration_minutes=profile.slot_duration_minutes,
        work_start_time=profile.work_start_time,
        work_end_time=profile.work_end_time,
    )


@router.put("/admin/schedule/settings", response_model=BarberSettingsResponse)
async def update_schedule_settings(
    body: BarberSettingsRequest,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Berberin çalışma saatlerini ve slot süresini oluşturur veya günceller.
    Kayıt yoksa oluşturur, varsa günceller (upsert).
    slot_duration_minutes: 30, 40 veya 60 dakika olabilir.
    """
    profile = await schedule_service.upsert_barber_settings(
        db,
        admin.tenant_id,
        body.slot_duration_minutes,
        body.work_start_time,
        body.work_end_time,
    )
    return BarberSettingsResponse(
        slot_duration_minutes=profile.slot_duration_minutes,
        work_start_time=profile.work_start_time,
        work_end_time=profile.work_end_time,
    )


# ─── Admin: Günlük Override ───────────────────────────────────────────────────

@router.post("/admin/schedule/override", status_code=200)
async def set_day_override(
    body: DayOverrideRequest,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Belirli bir gün için özel çalışma saatleri veya tatil ayarlar.
    Aynı tarihe ikinci kez çağrılırsa mevcut override güncellenir (upsert).
    is_closed=True ise o gün tamamen kapalıdır.
    """
    await schedule_service.upsert_day_override(
        db,
        admin.tenant_id,
        body.date,
        body.is_closed,
        body.work_start_time,
        body.work_end_time,
    )
    return {"message": "override_set"}


# ─── Admin: Slot Bloklama / Açma ─────────────────────────────────────────────

@router.post("/admin/slots/block", response_model=BlockSlotResponse, status_code=201)
async def block_slot(
    body: BlockSlotRequest,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Belirtilen slot zamanını kapatır.

    O slotta confirmed randevu varsa 409 döner:
    {"error": "slot_has_booking", "booking_id": "..."}
    Admin önce randevuyu iptal etmeli (ADIM 7), ardından slotu kapatabilir.
    """
    block = await schedule_service.block_slot(
        db, admin.tenant_id, body.slot_datetime, body.reason
    )
    return BlockSlotResponse(
        id=block.id,          # UUID tipinde — str cast gereksizdi
        blocked_at=block.blocked_at,
        reason=block.reason,
    )


@router.delete("/admin/slots/block/{block_id}", status_code=200)
async def unblock_slot(
    block_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Belirtilen blok kaydını siler ve slotu tekrar açar.
    Blok bulunamazsa veya farklı tenant'a aitse 404 döner.
    """
    await schedule_service.unblock_slot(db, admin.tenant_id, block_id)
    return {"message": "slot_unblocked"}


# ---------------------------------------------------------
# Admin: Bloklu Slot Listesi
# ---------------------------------------------------------

@router.get("/admin/slots/blocks", response_model=BlockedSlotsResponse)
async def get_blocked_slots(
    date: date = Query(..., description="Tarih: YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin icin: belirli gunun bloklu slotlarini dondurur.
    Bu endpoint block_id bilgisini UI'ya tasir.
    """
    # Bloklari service katmanindan al (tenant filtreli)
    blocks = await schedule_service.get_blocks_for_date(
        db,
        admin.tenant_id,
        date,
    )

    # Response seklinde dondur
    return BlockedSlotsResponse(
        date=date,
        blocks=[
            BlockedSlotItem(
                id=b.id,
                blocked_at=b.blocked_at,
                reason=b.reason,
            )
            for b in blocks
        ],
    )
