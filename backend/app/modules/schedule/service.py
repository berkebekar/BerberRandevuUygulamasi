"""
schedule/service.py — Slot hesaplama motoru ve çizelge yönetimi.

Bu dosyanın kalbi get_slots_for_date() fonksiyonudur.
Slotlar veritabanında saklanmaz; her istekte şu 4 kaynaktan hesaplanır:
  1. BarberProfile  → varsayılan çalışma saatleri ve slot süresi
  2. DayOverride   → o gün için özel saat veya tatil
  3. SlotBlock     → admin'in kapattığı tekil slotlar
  4. Booking       → müşterilerin aldığı randevular

Timezone: tüm işlemler Europe/Istanbul (UTC+3) üzerinden yürür.
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
    SlotItem,
    SlotStatus,
    WeekSlots,
)

logger = logging.getLogger(__name__)

# Projenin tek timezone'u — değiştirilemez (CLAUDE.md)
TZ = ZoneInfo("Europe/Istanbul")
DEFAULT_MAX_BOOKING_DAYS_AHEAD = 14


# ─── Yardımcı: Timezone normalize ────────────────────────────────────────────

def _to_utc(dt: datetime) -> datetime:
    """
    Herhangi bir datetime'ı UTC'ye çevirir.
    DB'den gelen naive datetime → UTC olarak kabul edilir.
    Timezone-aware datetime → direkt UTC'ye çevrilir.
    """
    if dt.tzinfo is None:
        # asyncpg bazen naive UTC döndürebilir
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _resolve_max_booking_days_ahead(profile: BarberProfile | None) -> int:
    """BarberProfile kaydindan ileri tarih limitini guvenli sekilde cozer."""
    if profile is None:
        return DEFAULT_MAX_BOOKING_DAYS_AHEAD
    raw_value = getattr(profile, "max_booking_days_ahead", DEFAULT_MAX_BOOKING_DAYS_AHEAD)
    if isinstance(raw_value, int) and raw_value > 0:
        return raw_value
    return DEFAULT_MAX_BOOKING_DAYS_AHEAD


def _resolve_slot_duration_minutes(profile: BarberProfile, override: DayOverride | None) -> int:
    """Gunluk slot suresini cozer: override varsa onu, yoksa profil degerini kullanir."""
    if override is not None:
        raw_value = getattr(override, "slot_duration_minutes", None)
        if isinstance(raw_value, int) and raw_value > 0:
            return raw_value
    return profile.slot_duration_minutes


# ─── Yardımcı: Tek gün slot üretimi ──────────────────────────────────────────

def _build_day_slots(
    profile: BarberProfile,
    override: DayOverride | None,
    bookings: list,
    blocks: list,
    target_date: date,
    now: datetime,
) -> DaySlots:
    """
    Bir güne ait tüm slotları hesaplayıp döndürür.

    Bu fonksiyon saf hesaplama yapar — DB çağrısı yapmaz.
    Veriler dışarıdan (service fonksiyonlarından) geçirilir.

    Öncelik sırası:
      1. past    — slot zamanı now'dan önce
      2. booked  — confirmed randevu var
      3. blocked — admin kapattı
      4. available — serbest
    """
    # Haftalık kapalı gün kontrolü
    weekday = target_date.weekday()
    max_booking_days_ahead = _resolve_max_booking_days_ahead(profile)
    if profile.weekly_closed_days and weekday in profile.weekly_closed_days:
        return DaySlots(
            date=target_date,
            is_closed=True,
            max_booking_days_ahead=max_booking_days_ahead,
            slots=[],
        )

    # DayOverride var ve gün kapalıysa: hiç slot üretme
    if override and override.is_closed:
        return DaySlots(
            date=target_date,
            is_closed=True,
            max_booking_days_ahead=max_booking_days_ahead,
            slots=[],
        )

    # Çalışma saatlerini belirle: override varsa override'ı, yoksa profile'ı kullan
    start_time = (
        override.work_start_time
        if override and override.work_start_time
        else profile.work_start_time
    )
    end_time = (
        override.work_end_time
        if override and override.work_end_time
        else profile.work_end_time
    )
    duration = timedelta(minutes=_resolve_slot_duration_minutes(profile, override))

    # Tüm slot zamanlarını üret: start, start+dur, start+2*dur, ...
    # Istanbul timezone'unda aware datetime'lar oluşturuyoruz
    slot_datetimes: list[datetime] = []
    current = datetime.combine(target_date, start_time, tzinfo=TZ)
    day_end = datetime.combine(target_date, end_time, tzinfo=TZ)

    while current + duration <= day_end:
        # Slot başlangıcı + süre ≤ günün bitiş saati → geçerli slot
        slot_datetimes.append(current)
        current += duration

    # Booked ve blocked zamanları UTC set'e dönüştür — hızlı arama için
    booked_utc: set[datetime] = {_to_utc(b.slot_time) for b in bookings}
    blocked_utc: set[datetime] = {_to_utc(b.blocked_at) for b in blocks}

    slots: list[SlotItem] = []
    for slot_dt in slot_datetimes:
        slot_utc = _to_utc(slot_dt)  # Karşılaştırma için UTC'ye çevir

        if slot_dt <= now:
            # Zaman geçmiş veya tam şu an — artık rezerve edilemez
            status = SlotStatus.past
        elif slot_utc in booked_utc:
            # Confirmed randevu mevcut
            status = SlotStatus.booked
        elif slot_utc in blocked_utc:
            # Admin bu slotu kapattı
            status = SlotStatus.blocked
        else:
            status = SlotStatus.available

        slots.append(SlotItem(
            time=slot_dt.strftime("%H:%M"),   # "09:00" formatı — gösterim için
            datetime=slot_dt,
            end_datetime=slot_dt + duration,
            status=status,
        ))

    return DaySlots(
        date=target_date,
        is_closed=False,
        max_booking_days_ahead=max_booking_days_ahead,
        slots=slots,
    )


# ─── Slot Okuma ───────────────────────────────────────────────────────────────

async def get_slots_for_date(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
    now: datetime | None = None,
) -> DaySlots:
    """
    Belirli bir gün için slot listesini hesaplar ve döndürür.

    'now' parametresi test ortamında zaman kontrolü için geçilebilir;
    prod'da None bırakılırsa gerçek saat kullanılır.

    Returns:
        DaySlots: Günün slot listesi (is_closed=True ise slots boş).
    """
    if now is None:
        now = datetime.now(TZ)  # Gerçek Istanbul saatini kullan

    # 1. BarberProfile: berber kayıt yapmamışsa boş liste döndür
    profile_result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        # Berber henüz çalışma ayarlarını girmemiş — boş liste
        return DaySlots(
            date=target_date,
            is_closed=False,
            max_booking_days_ahead=DEFAULT_MAX_BOOKING_DAYS_AHEAD,
            slots=[],
        )

    # 2. DayOverride: bu gün için özel ayar var mı?
    override_result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date == target_date,
        )
    )
    override = override_result.scalar_one_or_none()

    # Gün kapalıysa booking ve block sorgusu yapmadan erken dön
    # (is_closed=True → bu gün berber çalışmıyor, listelenecek slot yok)
    if override and override.is_closed:
        return DaySlots(
            date=target_date,
            is_closed=True,
            max_booking_days_ahead=_resolve_max_booking_days_ahead(profile),
            slots=[],
        )

    # 3. Gün için confirmed bookings'i çek
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

    # 4. Gün için slot_blocks'ları çek
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
    start_date'den başlayarak 7 günlük slot listesini döndürür.

    Performans optimizasyonu: bookings ve blocks tek sorguda çekilir,
    ardından her gün için Python tarafında filtrelenir.
    Böylece 14 ayrı DB sorgusu yerine 4 sorgu yapılır.
    """
    if now is None:
        now = datetime.now(TZ)

    # 1. BarberProfile
    profile_result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        # Ayar yok → tüm 7 gün için boş liste
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

    # 2. Haftalık DayOverride'ları tek sorguda çek
    week_end_date = start_date + timedelta(days=6)
    overrides_result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date >= start_date,
            DayOverride.date <= week_end_date,
        )
    )
    overrides = overrides_result.scalars().all()
    # Tarihe göre dict yap — O(1) erişim için
    overrides_by_date: dict[date, DayOverride] = {o.date: o for o in overrides}

    # 3. Haftalık confirmed bookings'i tek sorguda çek
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

    # 4. Haftalık slot_blocks'ları tek sorguda çek
    blocks_result = await db.execute(
        select(SlotBlock).where(
            SlotBlock.tenant_id == tenant_id,
            SlotBlock.blocked_at >= week_start_dt,
            SlotBlock.blocked_at <= week_end_dt,
        )
    )
    all_blocks = blocks_result.scalars().all()

    # Her gün için hesapla — booking ve block'ları gün bazında filtrele
    week_days: list[DaySlots] = []
    for i in range(7):
        d = start_date + timedelta(days=i)

        # Bu güne ait booking ve block'ları filtrele
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


# ─── Admin: Berber Ayarları ───────────────────────────────────────────────────

async def get_barber_settings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> BarberProfile | None:
    """
    Berberin çalışma ayarlarını döndürür.
    Kayıt yoksa None döner (henüz ayar girilmemiş demektir).
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
    Berber çalışma ayarlarını oluşturur veya günceller (upsert).

    Kayıt yoksa → yeni BarberProfile oluşturur.
    Kayıt varsa → mevcut kaydı günceller.

    Returns:
        BarberProfile: Güncellenmiş veya yeni oluşturulmuş kayıt.
    """
    existing = await get_barber_settings(db, tenant_id)

    if existing:
        # Mevcut kaydı güncelle
        existing.slot_duration_minutes = slot_duration_minutes
        existing.work_start_time = work_start_time
        existing.work_end_time = work_end_time
        existing.weekly_closed_days = weekly_closed_days
        existing.max_booking_days_ahead = max_booking_days_ahead
        # updated_at modelde onupdate yok; her güncellemede manuel set et
        existing.updated_at = datetime.now(timezone.utc)
    else:
        # İlk kez ayar giriliyor
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


# ─── Admin: Günlük Override ───────────────────────────────────────────────────

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
    Belirtilen gün için DayOverride oluşturur veya günceller (upsert).

    is_closed=True ise o gün berber çalışmıyor;
    is_closed=False ise work_start/end_time override olarak uygulanır.

    Returns:
        DayOverride: Güncellenmiş veya yeni oluşturulmuş override.
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
        # Mevcut override'ı güncelle
        override.is_closed = is_closed
        override.work_start_time = None if is_closed else work_start_time
        override.work_end_time = None if is_closed else work_end_time
        override.slot_duration_minutes = None if is_closed else slot_duration_minutes
    else:
        # Yeni override oluştur
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


# ─── Admin: Slot Bloklama / Açma ─────────────────────────────────────────────

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
    Belirtilen slot zamanını kapatır (SlotBlock kaydı oluşturur).

    Eğer o slotta confirmed randevu varsa 409 fırlatır:
    admin önce randevuyu iptal etmeli, ardından slotu kapatabilir.
    (CURSOR_PROMPTS ADIM 6 kuralı)

    Returns:
        SlotBlock: Yeni oluşturulan blok kaydı.
    """
    # O slotta confirmed randevu var mı?
    booking_result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.slot_time == slot_datetime,
            Booking.status == BookingStatus.confirmed,
        )
    )
    existing_booking = booking_result.scalar_one_or_none()

    if existing_booking:
        # Randevu iptal edilmeden slot kapatılamaz (CURSOR_PROMPTS kuralı)
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
        # Aynı slotu iki kez kapatmaya çalışmak anlamsız — idempotent değil, 409
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
    Belirtilen blok kaydını siler (slotu tekrar açar).

    Kayıt bulunamazsa veya farklı tenant'a aitse 404 fırlatır.
    Tenant filtresi zorunlu — başka tenant'ın bloğu silinemez (CLAUDE.md).
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




