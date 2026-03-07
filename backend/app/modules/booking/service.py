"""
booking/service.py â€” Randevu oluÅŸturma ve yÃ¶netim iÅŸlemleri.

Bu dosya sistemin en kritik parÃ§asÄ±dÄ±r.
Ã‡ift randevu oluÅŸmasÄ±nÄ± buradaki transaction ve kilit kurallarÄ± engeller.

Temel prensip (CLAUDE.md): Her randevu iÅŸlemi atomik olmalÄ±.
- SELECT FOR UPDATE: Mevcut randevu veya bloÄŸu kilitler
- Partial unique index: DB seviyesinde Ã§akÄ±ÅŸmayÄ± engeller
- IntegrityError yakalama: EÅŸzamanlÄ± ekleme denemelerini 409'a Ã§evirir

Timezone: TÃ¼m iÅŸlemler Europe/Istanbul (UTC+3) Ã¼zerinden yÃ¼rÃ¼r.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barber_profile import BarberProfile
from app.models.booking import Booking
from app.models.day_override import DayOverride
from app.models.enums import BookingStatus, CancelledBy
from app.models.slot_block import SlotBlock
from app.models.user import User

logger = logging.getLogger(__name__)

# Projenin tek timezone'u â€” deÄŸiÅŸtirilemez (CLAUDE.md)
TZ = ZoneInfo("Europe/Istanbul")

# Randevu alÄ±nabilecek maksimum ileri tarih (CLAUDE.md: 7 gÃ¼n kuralÄ±)
MAX_DAYS_AHEAD = 7

# Ayni kullanicinin ayni gun alabilecegi maksimum confirmed randevu sayisi.
MAX_BOOKINGS_PER_DAY = 3
USER_CANCELLATION_MINUTES_BEFORE = 15


def _to_local_tz(dt: datetime) -> datetime:
    """
    DB'den gelen datetime'i guvenli sekilde Istanbul timezone'una cevirir.
    Naive deger gelirse UTC kabul edilip Istanbul'a donusturulur.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).astimezone(TZ)
    return dt.astimezone(TZ)


# â”€â”€â”€ YardÄ±mcÄ±: Slot Takvimde GeÃ§erli mi? â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def _validate_slot_in_schedule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    slot_local: datetime,
) -> bool:
    """
    Verilen slot zamanÄ±nÄ±n berber takvimine gÃ¶re geÃ§erli olup olmadÄ±ÄŸÄ±nÄ± kontrol eder.

    Kontrol sÄ±rasÄ±:
    1. BarberProfile mevcut mu? (berber Ã§alÄ±ÅŸma ayarlarÄ± girilmiÅŸ mi?)
    2. GÃ¼n kapalÄ± mÄ±? (DayOverride.is_closed=True)
    3. Slot Ã§alÄ±ÅŸma saatleri iÃ§inde mi?
    4. Slot, slot sÃ¼resiyle hizalÄ± mÄ±? (Ã¶rn: 30dk slotlar iÃ§in 09:15 geÃ§ersizdir)
    5. Son slot + sÃ¼re â‰¤ gÃ¼n sonu mu?

    Bu fonksiyon booking/block durumunu KONTROL ETMEZ â€”
    bu kontroller transaction iÃ§inde SELECT FOR UPDATE ile yapÄ±lÄ±r.

    Returns:
        True: Slot geÃ§erli, False: Slot takvimde yok.
    """
    # BarberProfile: berber ayar girmemiÅŸse slot olamaz
    profile_result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        # Berber henÃ¼z Ã§alÄ±ÅŸma ayarlarÄ±nÄ± girmemiÅŸ â€” geÃ§ersiz slot
        return False

    # Haftalik kapali gunlerde slot gecersizdir.
    weekly_closed_days = getattr(profile, "weekly_closed_days", []) or []
    if slot_local.weekday() in weekly_closed_days:
        return False

    # DayOverride: o gÃ¼n iÃ§in Ã¶zel ayar var mÄ±?
    override_result = await db.execute(
        select(DayOverride).where(
            DayOverride.tenant_id == tenant_id,
            DayOverride.date == slot_local.date(),
        )
    )
    override = override_result.scalar_one_or_none()

    # GÃ¼n tamamen kapalÄ±ysa slot olamaz
    if override and override.is_closed:
        return False

    # Ã‡alÄ±ÅŸma saatlerini belirle: override varsa onu, yoksa profile'Ä± kullan
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
    duration_minutes = profile.slot_duration_minutes
    duration = timedelta(minutes=duration_minutes)

    # GÃ¼nÃ¼n baÅŸlangÄ±Ã§ ve bitiÅŸ zamanlarÄ±nÄ± Ä°stanbul timezone'unda oluÅŸtur
    day_start = datetime.combine(slot_local.date(), start_time, tzinfo=TZ)
    day_end = datetime.combine(slot_local.date(), end_time, tzinfo=TZ)

    # Slot Ã§alÄ±ÅŸma saatleri aralÄ±ÄŸÄ±nda mÄ±?
    if slot_local < day_start or slot_local >= day_end:
        # Slot Ã§alÄ±ÅŸma saatlerinin dÄ±ÅŸÄ±nda
        return False

    # Slot + sÃ¼re, gÃ¼n sonunu geÃ§iyor mu?
    if slot_local + duration > day_end:
        # Bu slotu aÃ§tÄ±ÄŸÄ±mÄ±zda gÃ¼n biter â€” geÃ§ersiz
        return False

    # Slot, slot sÃ¼resiyle hizalÄ± mÄ±?
    # Ã–rnek: 30dk slotlar iÃ§in 09:15 hizalÄ± deÄŸil, 09:00 ve 09:30 hizalÄ±dÄ±r
    elapsed = slot_local - day_start
    elapsed_seconds = int(elapsed.total_seconds())
    duration_seconds = int(duration.total_seconds())

    if elapsed_seconds % duration_seconds != 0:
        # Slot zamanÄ± slot sÃ¼resiyle hizalÄ± deÄŸil
        return False

    return True


# â”€â”€â”€ Randevu OluÅŸturma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def create_booking(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    slot_time: datetime,
    confirm_additional_same_day: bool = False,
) -> Booking:
    """
    Atomik randevu oluÅŸturur.

    Bu fonksiyonun Ã§alÄ±ÅŸma sÄ±rasÄ±:
    1. Ä°ÅŸ kurallarÄ± kontrolÃ¼ (transaction dÄ±ÅŸÄ± â€” kilit gerekmez):
       - GeÃ§miÅŸ slot mu? â†’ 400
       - 7 gÃ¼nden uzakta mÄ±? â†’ 400
       - Slot takvimde geÃ§erli mi? â†’ 400
    2. Atomik transaction (SELECT FOR UPDATE ile kilitli kontroller):
       - Bu slota confirmed randevu var mÄ±? â†’ 409 slot_taken
       - Bu slot bloklu mu? â†’ 409 slot_blocked
       - KullanÄ±cÄ±nÄ±n bugunku confirmed sayisi kontrolu:
         - 1 veya 2 randevusu varsa ve onay verilmediyse 409 additional_booking_confirmation_required
         - 3 ve uzeri ise 409 daily_booking_limit_exceeded
       - INSERT booking
    3. IntegrityError yakalama: eÅŸzamanlÄ± ekleme denemesi â†’ 409

    SELECT FOR UPDATE'in amacÄ±:
    AynÄ± anda iki istek geldiÄŸinde, biri diÄŸeri commit/rollback yapana kadar bekler.
    Bu "race condition" (yarÄ±ÅŸ durumu) korumasÄ±nÄ± saÄŸlar.

    Returns:
        Booking: OluÅŸturulan randevu kaydÄ±.

    Raises:
        400 slot_in_past: Slot zamanÄ± geÃ§miÅŸte
        400 too_far_in_future: Slot 7 gÃ¼nden daha ileri
        400 invalid_slot: Slot berber takvimine gÃ¶re geÃ§ersiz
        409 slot_taken: Bu slotta zaten confirmed randevu var
        409 slot_blocked: Bu slot admin tarafÄ±ndan bloklanmÄ±ÅŸ
        409 additional_booking_confirmation_required: Ek randevu icin kullanici onayi gerekir
        409 daily_booking_limit_exceeded: Ayni gun en fazla 3 randevu alinabilir
    """
    now = datetime.now(TZ)

    # Slot zamanÄ±nÄ± Ä°stanbul timezone'una Ã§evir â€” karÅŸÄ±laÅŸtÄ±rma tutarlÄ± olsun
    slot_local = slot_time.astimezone(TZ)

    # Kural 1: Slot geÃ§miÅŸte mi?
    if slot_local <= now:
        # GeÃ§miÅŸ veya tam ÅŸu anki slota randevu alÄ±namaz (CLAUDE.md)
        raise HTTPException(400, {"error": "slot_in_past"})

    # Kural 2: 7 gÃ¼nden daha ileri bir tarihe randevu alÄ±namaz
    if slot_local > now + timedelta(days=MAX_DAYS_AHEAD):
        raise HTTPException(400, {"error": "too_far_in_future"})

    # Kural 3: Slot berber takvimine gÃ¶re geÃ§erli mi?
    if not await _validate_slot_in_schedule(db, tenant_id, slot_local):
        # Slot Ã§alÄ±ÅŸma saatlerinde yok veya berber ayarÄ± girilmemiÅŸ
        raise HTTPException(400, {"error": "invalid_slot"})

    # GÃ¼nÃ¼n baÅŸlangÄ±cÄ± ve sonu (aynÄ± gÃ¼n ikinci randevu kontrolÃ¼ iÃ§in)
    day_start = datetime.combine(slot_local.date(), time.min, tzinfo=TZ)
    day_end = datetime.combine(slot_local.date(), time.max, tzinfo=TZ)

    try:
        # â”€â”€ Atomik transaction: TÃ¼m kontroller ve INSERT aynÄ± transaction'da â”€â”€
        # Autobegin: ilk execute() transaction'Ä± baÅŸlatÄ±r.
        # SELECT FOR UPDATE: bu sorgu satÄ±rÄ± kilitler â€”
        # baÅŸka bir transaction aynÄ± satÄ±rÄ± deÄŸiÅŸtirmek isterse sÄ±rada bekler.

        # Kontrol 1: Bu slotta confirmed randevu var mÄ±?
        result = await db.execute(
            select(Booking).where(
                Booking.tenant_id == tenant_id,
                Booking.slot_time == slot_local,
                Booking.status == BookingStatus.confirmed,
            )
            .with_for_update()  # Bu satÄ±rÄ± kilitle â€” Ã§ift randevu engellemek iÃ§in
        )
        if result.scalar_one_or_none():
            # Slot dolu â€” baÅŸka biri bu slotu aldÄ±
            raise HTTPException(409, {"error": "slot_taken"})

        # Kontrol 2: Slot admin tarafÄ±ndan bloklanmÄ±ÅŸ mÄ±?
        result = await db.execute(
            select(SlotBlock).where(
                SlotBlock.tenant_id == tenant_id,
                SlotBlock.blocked_at == slot_local,
            )
            .with_for_update()  # Blok kaydÄ±nÄ± kilitle
        )
        if result.scalar_one_or_none():
            # Slot kapalÄ± â€” admin bu saati engellemiÅŸ
            raise HTTPException(409, {"error": "slot_blocked"})

        # Kontrol 3: KullanÄ±cÄ±nÄ±n ayni gundeki confirmed randevu sayisini al.
        # Not: Bu sorguda tum kayitlar cekilir; sayi ve limit kontrolu service katmaninda yapilir.
        result = await db.execute(
            select(Booking).where(
                Booking.tenant_id == tenant_id,
                Booking.user_id == user_id,
                Booking.status == BookingStatus.confirmed,
                Booking.slot_time >= day_start,
                Booking.slot_time <= day_end,
            )
            .with_for_update()  # KullanÄ±cÄ±nÄ±n gÃ¼nlÃ¼k randevusunu kilitle
        )
        existing_same_day_bookings = list(result.scalars().all())
        existing_count = len(existing_same_day_bookings)

        # Ayni gun 3 sinirini astiginda yeni randevuya izin verme.
        if existing_count >= MAX_BOOKINGS_PER_DAY:
            raise HTTPException(
                409,
                {
                    "error": "daily_booking_limit_exceeded",
                    "current_count": existing_count,
                    "max_allowed": MAX_BOOKINGS_PER_DAY,
                },
            )

        # Kullanici ayni gun ilk ek randevuyu alirken acik onay istenir.
        if existing_count >= 1 and not confirm_additional_same_day:
            raise HTTPException(
                409,
                {
                    "error": "additional_booking_confirmation_required",
                    "current_count": existing_count,
                    "max_allowed": MAX_BOOKINGS_PER_DAY,
                },
            )

        # TÃ¼m kontroller geÃ§ti â€” randevuyu oluÅŸtur
        booking = Booking(
            tenant_id=tenant_id,
            user_id=user_id,
            slot_time=slot_local,
            status=BookingStatus.confirmed,
        )
        db.add(booking)
        await db.commit()  # Transaction'Ä± tamamla â€” kilit Ã§Ã¶zÃ¼lÃ¼r
        await db.refresh(booking)  # Sunucu tarafÄ±ndan oluÅŸturulan id ve created_at'i yÃ¼kle
        return booking

    except HTTPException:
        # FastAPI HTTP hatalarÄ±nÄ± aynen tekrar fÄ±rlat â€” rollback yap
        await db.rollback()
        raise

    except IntegrityError as e:
        # EÅŸzamanlÄ± istek durumu: iki transaction aynÄ± anda geÃ§ti ve aynÄ± satÄ±rÄ± eklemeye Ã§alÄ±ÅŸtÄ±.
        # Partial unique index (ix_bookings_tenant_slot_confirmed) ihlali â†’ 409
        await db.rollback()
        # Slot iÃ§in concurrent istek Ã¶nce commit etti.
        logger.warning("Booking IntegrityError | tenant_id=%s | user_id=%s | error=%s", tenant_id, user_id, e)
        raise HTTPException(409, {"error": "slot_taken"})


# â”€â”€â”€ KullanÄ±cÄ±: Kendi RandevularÄ±nÄ± Listele â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_user_bookings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[Booking]:
    """
    KullanÄ±cÄ±nÄ±n tÃ¼m randevularÄ±nÄ± dÃ¶ndÃ¼rÃ¼r (confirmed ve cancelled).
    Yeniden eskiye sÄ±ralÄ±dÄ±r (slot_time DESC).

    Tenant filtresi zorunlu (CLAUDE.md): baÅŸka tenant'Ä±n randevularÄ± gÃ¶rÃ¼lemez.
    """
    result = await db.execute(
        select(Booking)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.user_id == user_id,
        )
        .order_by(Booking.slot_time.desc())
    )
    return list(result.scalars().all())


# â”€â”€â”€ Admin: GÃ¼nlÃ¼k Randevu Listesi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_bookings_by_date(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> list[tuple[Booking, User]]:
    """
    Belirli bir gÃ¼n iÃ§in tÃ¼m randevularÄ± ve mÃ¼ÅŸteri bilgilerini dÃ¶ndÃ¼rÃ¼r.
    Admin paneli gÃ¼nlÃ¼k gÃ¶rÃ¼nÃ¼mÃ¼ iÃ§in kullanÄ±lÄ±r.

    Returns:
        List[Tuple[Booking, User]]: Randevu + mÃ¼ÅŸteri Ã§iftleri, slot_time ASC sÄ±ralÄ±.
    """
    day_start = datetime.combine(target_date, time.min, tzinfo=TZ)
    day_end = datetime.combine(target_date, time.max, tzinfo=TZ)

    # Booking ve User tablosunu JOIN ile Ã§ek â€” ayrÄ± sorgu yapmaktan daha verimli
    result = await db.execute(
        select(Booking, User)
        .join(User, User.id == Booking.user_id)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.slot_time >= day_start,
            Booking.slot_time <= day_end,
        )
        .order_by(Booking.slot_time.asc())
    )
    return list(result.all())


# â”€â”€â”€ Admin: Randevu Ä°ptal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def cancel_booking_admin(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    booking_id: uuid.UUID,
) -> tuple[Booking, str | None]:
    """
    Admin tarafÄ±ndan randevu iptali.

    Ã‡alÄ±ÅŸma sÄ±rasÄ±:
    1. Randevuyu bul (tenant_id filtreli â€” baÅŸka tenant'Ä±n randevusu deÄŸiÅŸtirilemez)
    2. Zaten iptal mÄ±? â†’ 404 (idempotent deÄŸil; admin ikinci kez iptal edemez)
    3. status='cancelled', cancelled_by='admin' yap
    4. Commit
    5. (Caller sorumluluÄŸu) Notification background task: booking/router.py Ã§aÄŸÄ±rÄ±r

    Returns:
        tuple[Booking, str | None]:
            - Booking: Ä°ptal edilmiÅŸ randevu
            - str | None: MÃ¼ÅŸterinin telefon numarasÄ± (SMS iÃ§in); kullanÄ±cÄ± bulunamazsa None

    Raises:
        404 booking_not_found: Randevu bulunamadÄ± veya zaten iptal
    """
    # Randevuyu tenant_id filtresiyle ara (CLAUDE.md: her sorguda tenant_id zorunlu)
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.tenant_id == tenant_id,
        )
    )
    booking = result.scalar_one_or_none()

    if booking is None:
        # Randevu yok ya da baÅŸka tenant'a ait â€” 404
        raise HTTPException(404, {"error": "booking_not_found"})

    if booking.status != BookingStatus.confirmed:
        # Sadece aktif (confirmed) randevular iptal edilebilir
        raise HTTPException(404, {"error": "booking_not_found"})

    # Iptal sadece randevu saatinden once yapilabilir
    now_local = datetime.now(TZ)
    booking_local = _to_local_tz(booking.slot_time)
    if booking_local <= now_local:
        raise HTTPException(409, {"error": "booking_cancellation_window_passed"})

    # MÃ¼ÅŸteriyi bul â€” notification background task iÃ§in telefon numarasÄ± lazÄ±m
    user_result = await db.execute(
        select(User).where(
            User.id == booking.user_id,
            User.tenant_id == tenant_id,
        )
    )
    user = user_result.scalar_one_or_none()
    user_phone = user.phone if user else None

    # Randevuyu iptal et
    booking.status = BookingStatus.cancelled
    booking.cancelled_by = CancelledBy.admin

    await db.commit()
    await db.refresh(booking)

    logger.info(
        "Booking cancelled by admin | booking_id=%s | tenant_id=%s",
        booking_id,
        tenant_id,
    )
    # user_phone: booking/router.py'nin notification background task'Ä± baÅŸlatmasÄ± iÃ§in
    return booking, user_phone


async def cancel_booking_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    booking_id: uuid.UUID,
) -> Booking:
    """
    Kullanici tarafindan randevu iptali.

    Kurallar:
    - Booking, ayni tenant ve ayni user'a ait olmali
    - Sadece confirmed booking iptal edilebilir
    - Slot saatine 15 dakikadan az kaldiysa (veya saat gectiyse) iptal edilemez
    """
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.tenant_id == tenant_id,
        )
    )
    booking = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(404, {"error": "booking_not_found"})

    if booking.user_id != user_id:
        raise HTTPException(404, {"error": "booking_not_found"})

    if booking.status != BookingStatus.confirmed:
        raise HTTPException(404, {"error": "booking_not_found"})

    now_local = datetime.now(TZ)
    booking_local = _to_local_tz(booking.slot_time)
    if booking_local - now_local < timedelta(minutes=USER_CANCELLATION_MINUTES_BEFORE):
        raise HTTPException(409, {"error": "booking_cancellation_window_passed"})

    booking.status = BookingStatus.cancelled
    booking.cancelled_by = CancelledBy.user

    await db.commit()
    await db.refresh(booking)
    return booking


async def set_booking_no_show_admin(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    booking_id: uuid.UUID,
) -> Booking:
    """
    Randevuyu "gerceklesmedi" (no_show) olarak isaretler.
    Sadece slot saati gelmis/gecmis ve status='confirmed' olan kayitlar icin gecerlidir.
    """
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.tenant_id == tenant_id,
        )
    )
    booking = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(404, {"error": "booking_not_found"})

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(404, {"error": "booking_not_found"})

    now_local = datetime.now(TZ)
    booking_local = _to_local_tz(booking.slot_time)
    if booking_local > now_local:
        raise HTTPException(409, {"error": "booking_not_started"})

    booking.status = BookingStatus.no_show
    booking.cancelled_by = None
    await db.commit()
    await db.refresh(booking)
    return booking


async def set_booking_confirmed_admin(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    booking_id: uuid.UUID,
) -> Booking:
    """
    no_show olan bir randevuyu tekrar "gerceklesti varsayilan" durumuna (confirmed) alir.
    Sadece slot saati gelmis/gecmis kayitlar icin gecerlidir.
    """
    result = await db.execute(
        select(Booking).where(
            Booking.id == booking_id,
            Booking.tenant_id == tenant_id,
        )
    )
    booking = result.scalar_one_or_none()

    if booking is None:
        raise HTTPException(404, {"error": "booking_not_found"})

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(404, {"error": "booking_not_found"})

    now_local = datetime.now(TZ)
    booking_local = _to_local_tz(booking.slot_time)
    if booking_local > now_local:
        raise HTTPException(409, {"error": "booking_not_started"})

    booking.status = BookingStatus.confirmed
    booking.cancelled_by = None
    await db.commit()
    await db.refresh(booking)
    return booking


# â”€â”€â”€ Admin: Manuel Randevu OluÅŸturma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def create_booking_admin(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    slot_time: datetime,
) -> Booking:
    """
    Admin tarafÄ±ndan manuel randevu oluÅŸturma.

    AynÄ± iÅŸ kurallarÄ± geÃ§erlidir (slot_in_past, too_far_in_future, invalid_slot,
    slot_taken, slot_blocked, already_booked_today).

    Admin neden randevu oluÅŸturabilir?
    Telefon ile gelen mÃ¼ÅŸteri iÃ§in admin sisteme elle randevu ekleyebilir.
    create_booking fonksiyonunu user_id ile Ã§aÄŸÄ±rÄ±r â€” mantÄ±k tekrar yazÄ±lmaz.
    """
    # create_booking'i admin iÃ§in de kullan â€” aynÄ± atomik mantÄ±k
    return await create_booking(
        db,
        tenant_id,
        user_id,
        slot_time,
        confirm_additional_same_day=True,
    )

