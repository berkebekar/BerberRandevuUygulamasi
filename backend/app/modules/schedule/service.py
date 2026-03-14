"""
schedule/service.py â€” Slot hesaplama motoru ve Ã§izelge yÃ¶netimi.

Bu dosyanÄ±n kalbi get_slots_for_date() fonksiyonudur.
Slotlar veritabanÄ±nda saklanmaz; her istekte ÅŸu 4 kaynaktan hesaplanÄ±r:
  1. BarberProfile  â†’ varsayÄ±lan Ã§alÄ±ÅŸma saatleri ve slot sÃ¼resi
  2. DayOverride   â†’ o gÃ¼n iÃ§in Ã¶zel saat veya tatil
  3. SlotBlock     â†’ admin'in kapattÄ±ÄŸÄ± tekil slotlar
  4. Booking       â†’ mÃ¼ÅŸterilerin aldÄ±ÄŸÄ± randevular

Timezone: tÃ¼m iÅŸlemler Europe/Istanbul (UTC+3) Ã¼zerinden yÃ¼rÃ¼r.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barber_profile import BarberProfile
from app.models.booking import Booking
from app.models.day_override import DayOverride
from app.models.enums import BookingStatus
from app.models.slot_block import SlotBlock
from app.modules.schedule.schemas import (
    BarberSettingsResponse,
    BlockSlotResponse,
    DaySlots,
    WeekSlots,
)
from app.modules.schedule.slot_engine import (
    build_day_slots,
    resolve_max_booking_days_ahead,
    to_utc,
)

logger = logging.getLogger(__name__)

# Projenin tek timezone'u â€” deÄŸiÅŸtirilemez (CLAUDE.md)
TZ = ZoneInfo("Europe/Istanbul")
DEFAULT_MAX_BOOKING_DAYS_AHEAD = 14


# â”€â”€â”€ YardÄ±mcÄ±: Timezone normalize â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _to_utc(dt: datetime) -> datetime:
    """
    Herhangi bir datetime'Ä± UTC'ye Ã§evirir.
    DB'den gelen naive datetime â†’ UTC olarak kabul edilir.
    Timezone-aware datetime â†’ direkt UTC'ye Ã§evrilir.
    """
    return to_utc(dt)

def _resolve_max_booking_days_ahead(profile: BarberProfile | None) -> int:
    """BarberProfile kaydindan ileri tarih limitini guvenli sekilde cozer."""
    return resolve_max_booking_days_ahead(profile)

# â”€â”€â”€ YardÄ±mcÄ±: Tek gÃ¼n slot Ã¼retimi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _build_day_slots(
    profile: BarberProfile,
    override: DayOverride | None,
    bookings: list,
    blocks: list,
    target_date: date,
    now: datetime,
) -> DaySlots:
    return build_day_slots(
        profile=profile,
        override=override,
        bookings=bookings,
        blocks=blocks,
        target_date=target_date,
        now=now,
    )


# â”€â”€â”€ Slot Okuma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_slots_for_date(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
    now: datetime | None = None,
) -> DaySlots:
    """
    Belirli bir gÃ¼n iÃ§in slot listesini hesaplar ve dÃ¶ndÃ¼rÃ¼r.

    'now' parametresi test ortamÄ±nda zaman kontrolÃ¼ iÃ§in geÃ§ilebilir;
    prod'da None bÄ±rakÄ±lÄ±rsa gerÃ§ek saat kullanÄ±lÄ±r.

    Returns:
        DaySlots: GÃ¼nÃ¼n slot listesi (is_closed=True ise slots boÅŸ).
    """
    if now is None:
        now = datetime.now(TZ)  # GerÃ§ek Istanbul saatini kullan

    # 1. BarberProfile: berber kayÄ±t yapmamÄ±ÅŸsa boÅŸ liste dÃ¶ndÃ¼r
    profile_result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        # Berber henÃ¼z Ã§alÄ±ÅŸma ayarlarÄ±nÄ± girmemiÅŸ â€” boÅŸ liste
        return DaySlots(
            date=target_date,
            is_closed=False,
            max_booking_days_ahead=DEFAULT_MAX_BOOKING_DAYS_AHEAD,
            slots=[],
        )

    # 2. DayOverride: bu gÃ¼n iÃ§in Ã¶zel ayar var mÄ±?
    override_result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date == target_date,
        )
    )
    override = override_result.scalar_one_or_none()

    # GÃ¼n kapalÄ±ysa booking ve block sorgusu yapmadan erken dÃ¶n
    # (is_closed=True â†’ bu gÃ¼n berber Ã§alÄ±ÅŸmÄ±yor, listelenecek slot yok)
    if override and override.is_closed:
        return DaySlots(
            date=target_date,
            is_closed=True,
            max_booking_days_ahead=_resolve_max_booking_days_ahead(profile),
            slots=[],
        )

    # 3. GÃ¼n iÃ§in confirmed bookings'i Ã§ek
    day_start = datetime.combine(target_date, time.min, tzinfo=TZ)
    day_end   = datetime.combine(target_date, time.max, tzinfo=TZ)

    bookings_result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.status == BookingStatus.confirmed,
            Booking.slot_time >= day_start,
            Booking.slot_time <= day_end,
        )
    )
    bookings = bookings_result.scalars().all()

    # 4. GÃ¼n iÃ§in slot_blocks'larÄ± Ã§ek
    blocks_result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.tenant_id == tenant_id,
            SlotBlock.blocked_at >= day_start,
            SlotBlock.blocked_at <= day_end,
        )
    )
    blocks = blocks_result.scalars().all()

    return _build_day_slots(profile, override, bookings, blocks, target_date, now)


async def get_slots_for_week(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    now: datetime | None = None,
) -> WeekSlots:
    """
    start_date'den baÅŸlayarak 7 gÃ¼nlÃ¼k slot listesini dÃ¶ndÃ¼rÃ¼r.

    Performans optimizasyonu: bookings ve blocks tek sorguda Ã§ekilir,
    ardÄ±ndan her gÃ¼n iÃ§in Python tarafÄ±nda filtrelenir.
    BÃ¶ylece 14 ayrÄ± DB sorgusu yerine 4 sorgu yapÄ±lÄ±r.
    """
    if now is None:
        now = datetime.now(TZ)

    # 1. BarberProfile
    profile_result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        # Ayar yok â†’ tÃ¼m 7 gÃ¼n iÃ§in boÅŸ liste
        empty_days = [
            DaySlots(
                date=start_date + timedelta(days=i),
                is_closed=False,
                max_booking_days_ahead=DEFAULT_MAX_BOOKING_DAYS_AHEAD,
                slots=[],
            )
            for i in range(7)
        ]
        return WeekSlots(week=empty_days)

    # 2. HaftalÄ±k DayOverride'larÄ± tek sorguda Ã§ek
    week_end_date = start_date + timedelta(days=6)
    overrides_result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date >= start_date,
            DayOverride.date <= week_end_date,
        )
    )
    overrides = overrides_result.scalars().all()
    # Tarihe gÃ¶re dict yap â€” O(1) eriÅŸim iÃ§in
    overrides_by_date: dict[date, DayOverride] = {o.date: o for o in overrides}

    # 3. HaftalÄ±k confirmed bookings'i tek sorguda Ã§ek
    week_start_dt = datetime.combine(start_date, time.min, tzinfo=TZ)
    week_end_dt   = datetime.combine(week_end_date, time.max, tzinfo=TZ)

    bookings_result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.status == BookingStatus.confirmed,
            Booking.slot_time >= week_start_dt,
            Booking.slot_time <= week_end_dt,
        )
    )
    all_bookings = bookings_result.scalars().all()

    # 4. HaftalÄ±k slot_blocks'larÄ± tek sorguda Ã§ek
    blocks_result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.tenant_id == tenant_id,
            SlotBlock.blocked_at >= week_start_dt,
            SlotBlock.blocked_at <= week_end_dt,
        )
    )
    all_blocks = blocks_result.scalars().all()

    # Her gÃ¼n iÃ§in hesapla â€” booking ve block'larÄ± gÃ¼n bazÄ±nda filtrele
    week_days: list[DaySlots] = []
    for i in range(7):
        d = start_date + timedelta(days=i)

        # Bu gÃ¼ne ait booking ve block'larÄ± filtrele
        day_bookings = [
            b for b in all_bookings
            if _to_utc(b.slot_time).astimezone(TZ).date() == d
        ]
        day_blocks = [
            b for b in all_blocks
            if _to_utc(b.blocked_at).astimezone(TZ).date() == d
        ]
        day_override = overrides_by_date.get(d)

        day_slots = _build_day_slots(profile, day_override, day_bookings, day_blocks, d, now)
        week_days.append(day_slots)

    return WeekSlots(week=week_days)


# â”€â”€â”€ Admin: Berber AyarlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_barber_settings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> BarberProfile | None:
    """
    Berberin Ã§alÄ±ÅŸma ayarlarÄ±nÄ± dÃ¶ndÃ¼rÃ¼r.
    KayÄ±t yoksa None dÃ¶ner (henÃ¼z ayar girilmemiÅŸ demektir).
    """
    result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def upsert_barber_settings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    slot_duration_minutes: int,
    work_start_time: time,
    work_end_time: time,
    weekly_closed_days: list[int],
    max_booking_days_ahead: int,
) -> BarberProfile:
    """
    Berber Ã§alÄ±ÅŸma ayarlarÄ±nÄ± oluÅŸturur veya gÃ¼nceller (upsert).

    KayÄ±t yoksa â†’ yeni BarberProfile oluÅŸturur.
    KayÄ±t varsa â†’ mevcut kaydÄ± gÃ¼nceller.

    Returns:
        BarberProfile: GÃ¼ncellenmiÅŸ veya yeni oluÅŸturulmuÅŸ kayÄ±t.
    """
    existing = await get_barber_settings(db, tenant_id)

    if existing:
        # Mevcut kaydÄ± gÃ¼ncelle
        existing.slot_duration_minutes = slot_duration_minutes
        existing.work_start_time = work_start_time
        existing.work_end_time = work_end_time
        existing.weekly_closed_days = weekly_closed_days
        existing.max_booking_days_ahead = max_booking_days_ahead
        # updated_at modelde onupdate yok; her gÃ¼ncellemede manuel set et
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # Ä°lk kez ayar giriliyor
        existing = BarberProfile(
            tenant_id=tenant_id,
            slot_duration_minutes=slot_duration_minutes,
            work_start_time=work_start_time,
            work_end_time=work_end_time,
            weekly_closed_days=weekly_closed_days,
            max_booking_days_ahead=max_booking_days_ahead,
        )
        db.add(existing)

    await db.commit()
    await db.refresh(existing)
    return existing


# â”€â”€â”€ Admin: GÃ¼nlÃ¼k Override â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def upsert_day_override(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
    is_closed: bool,
    work_start_time: time | None,
    work_end_time: time | None,
    slot_duration_minutes: int | None = None,
) -> DayOverride:
    """
    Belirtilen gÃ¼n iÃ§in DayOverride oluÅŸturur veya gÃ¼nceller (upsert).

    is_closed=True ise o gÃ¼n berber Ã§alÄ±ÅŸmÄ±yor;
    is_closed=False ise work_start/end_time override olarak uygulanÄ±r.

    Returns:
        DayOverride: GÃ¼ncellenmiÅŸ veya yeni oluÅŸturulmuÅŸ override.
    """
    result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date == target_date,
        )
    )
    override = result.scalar_one_or_none()

    if is_closed:
        day_start = datetime.combine(target_date, time.min, tzinfo=TZ)
        day_end = datetime.combine(target_date, time.max, tzinfo=TZ)
        booking_result = await db.execute(
            select(Booking).where(
                Booking.tenant_id == tenant_id,
                Booking.status == BookingStatus.confirmed,
                Booking.slot_time >= day_start,
                Booking.slot_time <= day_end,
            ).limit(1)
        )
        existing_booking = booking_result.scalar_one_or_none()
        if existing_booking is not None:
            raise HTTPException(
                409,
                {
                    "error": "override_has_confirmed_bookings",
                    "booking_id": str(existing_booking.id),
                },
            )

    if override:
        # Mevcut override'Ä± gÃ¼ncelle
        override.is_closed = is_closed
        override.work_start_time = None if is_closed else work_start_time
        override.work_end_time = None if is_closed else work_end_time
        override.slot_duration_minutes = None if is_closed else slot_duration_minutes
    else:
        # Yeni override oluÅŸtur
        override = DayOverride(
            tenant_id=tenant_id,
            date=target_date,
            is_closed=is_closed,
            work_start_time=None if is_closed else work_start_time,
            work_end_time=None if is_closed else work_end_time,
            slot_duration_minutes=None if is_closed else slot_duration_minutes,
        )
        db.add(override)

    await db.commit()
    await db.refresh(override)
    return override


# â”€â”€â”€ Admin: Slot Bloklama / AÃ§ma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_day_override(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> DayOverride | None:
    """Belirli bir gun icin override kaydini doner; yoksa None."""
    result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date == target_date,
        )
    )
    return result.scalar_one_or_none()


async def delete_day_override(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> None:
    """Belirli bir gunun override kaydini siler."""
    override = await get_day_override(db, tenant_id, target_date)
    if override is None:
        raise HTTPException(404, {"error": "override_not_found"})
    await db.delete(override)
    await db.commit()


async def block_slot(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    slot_datetime: datetime,
    reason: str | None = None,
) -> SlotBlock:
    """
    Belirtilen slot zamanÄ±nÄ± kapatÄ±r (SlotBlock kaydÄ± oluÅŸturur).

    EÄŸer o slotta confirmed randevu varsa 409 fÄ±rlatÄ±r:
    admin Ã¶nce randevuyu iptal etmeli, ardÄ±ndan slotu kapatabilir.
    (CURSOR_PROMPTS ADIM 6 kuralÄ±)

    Returns:
        SlotBlock: Yeni oluÅŸturulan blok kaydÄ±.
    """
    # O slotta confirmed randevu var mÄ±?
    booking_result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.slot_time == slot_datetime,
            Booking.status == BookingStatus.confirmed,
        )
    )
    existing_booking = booking_result.scalar_one_or_none()

    if existing_booking:
        # Randevu iptal edilmeden slot kapatÄ±lamaz (CURSOR_PROMPTS kuralÄ±)
        raise HTTPException(
            409,
            {"error": "slot_has_booking", "booking_id": str(existing_booking.id)},
        )

    # Zaten bloklu mu?
    block_result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.tenant_id == tenant_id,
            SlotBlock.blocked_at == slot_datetime,
        )
    )
    if block_result.scalar_one_or_none():
        # AynÄ± slotu iki kez kapatmaya Ã§alÄ±ÅŸmak anlamsÄ±z â€” idempotent deÄŸil, 409
        raise HTTPException(409, {"error": "slot_already_blocked"})

    block = SlotBlock(
        tenant_id=tenant_id,
        blocked_at=slot_datetime,
        reason=reason,
    )
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return block


async def unblock_slot(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    block_id: uuid.UUID,
) -> None:
    """
    Belirtilen blok kaydÄ±nÄ± siler (slotu tekrar aÃ§ar).

    KayÄ±t bulunamazsa veya farklÄ± tenant'a aitse 404 fÄ±rlatÄ±r.
    Tenant filtresi zorunlu â€” baÅŸka tenant'Ä±n bloÄŸu silinemez (CLAUDE.md).
    """
    result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.id == block_id,
            SlotBlock.tenant_id == tenant_id,  # Tenant izolasyonu (CLAUDE.md)
        )
    )
    block = result.scalar_one_or_none()

    if block is None:
        raise HTTPException(404, {"error": "block_not_found"})

    await db.delete(block)
    await db.commit()

# ---------------------------------------------------------
# Admin: Bloklu slot listesi
# ---------------------------------------------------------

async def get_blocks_for_date(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> list[SlotBlock]:
    """
    Belirli bir gun icin tum bloklu slotlari dondurur.
    Admin tarafinda slot acma islemi icin block_id gerekir.
    """
    # Gunun baslangic ve bitis zamanlarini Istanbul timezone'u ile olustur
    day_start = datetime.combine(target_date, time.min, tzinfo=TZ)
    day_end = datetime.combine(target_date, time.max, tzinfo=TZ)

    # Bu gun icindeki bloklari cek (tenant filtreli)
    result = await db.execute(
        select(SlotBlock)
        .where(
            SlotBlock.tenant_id == tenant_id,
            SlotBlock.blocked_at >= day_start,
            SlotBlock.blocked_at <= day_end,
        )
        .order_by(SlotBlock.blocked_at.asc())
    )

    # DB sonucunu listeye cevir
    return result.scalars().all()





