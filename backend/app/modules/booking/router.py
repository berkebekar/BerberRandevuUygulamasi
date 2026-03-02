"""
booking/router.py â€” Randevu HTTP endpoint'leri.

MÃ¼ÅŸteri endpoint'leri (user_session cookie gerektirir):
  POST /bookings                    â†’ Atomik randevu oluÅŸtur
  GET  /bookings/my                 â†’ Kendi randevularÄ±nÄ± listele

Admin endpoint'leri (admin_session cookie gerektirir):
  GET  /bookings?date=YYYY-MM-DD    â†’ Belirli gÃ¼n iÃ§in randevu listesi
  DELETE /bookings/{id}             â†’ Randevu iptal (cancelled_by='admin')
  POST /admin/bookings/{id}/mark-no-show   â†’ Gecmis randevuyu gerceklesmedi isaretle
  POST /admin/bookings/{id}/mark-confirmed â†’ Gecmis no_show randevuyu geri al
  POST /admin/bookings              â†’ Manuel randevu oluÅŸtur (belirli kullanÄ±cÄ± iÃ§in)

Business logic booking/service.py iÃ§indedir; bu dosya sadece HTTP katmanÄ±dÄ±r.
"""

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.admin import Admin
from app.models.enums import NotificationMessageType
from app.models.user import User
from app.modules.booking import service as booking_service
from app.modules.booking.schemas import (
    AdminBookingCreateRequest,
    BookingCreateRequest,
    BookingResponse,
    BookingWithUserResponse,
)
from app.modules.notification import service as notification_service
from app.modules.notification.provider import get_sms_provider

# Prefix yok â€” endpoint path'leri dekoratÃ¶rde tam olarak belirtiliyor.
# Ã‡Ã¼nkÃ¼ mÃ¼ÅŸteri endpoint'leri (/bookings) ve admin endpoint'leri (/admin/bookings)
# ortak bir prefix paylaÅŸmÄ±yor.
router = APIRouter(tags=["bookings"])


def _normalize_phone(phone: str | None) -> str | None:
    """
    Admin manuel formundan gelen telefon alanini normalize eder.
    Bos veya sadece bosluk olan degerleri None kabul eder.
    """
    if phone is None:
        return None
    normalized = phone.strip()
    return normalized if normalized else None


def _build_placeholder_phone() -> str:
    """
    Telefon bilinmiyorsa DB zorunluluklarini bozmayacak benzersiz bir deger uretir.
    User.phone nullable olmadigi icin None yerine placeholder kullanilir.
    """
    return f"no-phone-{uuid.uuid4().hex}"


# â”€â”€â”€ MÃ¼ÅŸteri: Randevu OluÅŸturma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    body: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Atomik randevu oluÅŸturur.

    TÃ¼m kontroller transaction iÃ§inde yapÄ±lÄ±r:
    - slot_in_past: GeÃ§miÅŸ slota randevu alÄ±namaz
    - too_far_in_future: 7 gÃ¼nden uzaÄŸa randevu alÄ±namaz
    - invalid_slot: Slot berber takvimine gÃ¶re geÃ§ersiz
    - slot_taken: Bu slotta zaten confirmed randevu var
    - slot_blocked: Bu slot admin tarafÄ±ndan kapatÄ±lmÄ±ÅŸ
    - already_booked_today: KullanÄ±cÄ± bu gÃ¼n iÃ§in zaten randevu almÄ±ÅŸ
    """
    booking = await booking_service.create_booking(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        slot_time=body.slot_time,
    )
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        slot_time=booking.slot_time,
        status=booking.status,
        cancelled_by=booking.cancelled_by,
        created_at=booking.created_at,
    )


# â”€â”€â”€ MÃ¼ÅŸteri: Kendi RandevularÄ±nÄ± Listeleme â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/bookings/my", response_model=list[BookingResponse])
async def get_my_bookings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    GiriÅŸ yapmÄ±ÅŸ kullanÄ±cÄ±nÄ±n tÃ¼m randevularÄ±nÄ± dÃ¶ndÃ¼rÃ¼r.
    Confirmed ve cancelled randevular dahildir.
    Yeniden eskiye (slot_time DESC) sÄ±ralÄ±dÄ±r.
    """
    bookings = await booking_service.get_user_bookings(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
    )
    return [
        BookingResponse(
            id=b.id,
            user_id=b.user_id,
            slot_time=b.slot_time,
            status=b.status,
            cancelled_by=b.cancelled_by,
            created_at=b.created_at,
        )
        for b in bookings
    ]


# â”€â”€â”€ Admin: GÃ¼nlÃ¼k Randevu Listesi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/bookings", response_model=list[BookingWithUserResponse])
async def get_bookings_by_date(
    date: date = Query(..., description="Tarih: YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin iÃ§in: belirli bir gÃ¼nÃ¼n randevu listesini dÃ¶ndÃ¼rÃ¼r.
    Her randevuda mÃ¼ÅŸteri adÄ±, soyadÄ± ve telefon bilgisi vardÄ±r.
    slot_time ASC (gÃ¼nÃ¼n erken saatinden geÃ§ saatine) sÄ±ralÄ±dÄ±r.
    """
    rows = await booking_service.get_bookings_by_date(
        db,
        tenant_id=admin.tenant_id,
        target_date=date,
    )
    return [
        BookingWithUserResponse(
            id=booking.id,
            user_id=booking.user_id,
            user_first_name=user.first_name,
            user_last_name=user.last_name,
            user_phone=user.phone,
            slot_time=booking.slot_time,
            status=booking.status,
            cancelled_by=booking.cancelled_by,
            created_at=booking.created_at,
        )
        for booking, user in rows
    ]


# â”€â”€â”€ Admin: Randevu Ä°ptal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.delete("/bookings/{booking_id}", response_model=BookingResponse)
async def cancel_booking(
    booking_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin randevuyu iptal eder.
    status='cancelled', cancelled_by='admin' olarak gÃ¼ncellenir.

    Ä°ptal sonrasÄ± SMS notification background task olarak gÃ¶nderilir:
    - NotificationLog oluÅŸturulur (status='pending' â†’ 'sent' veya 'failed')
    - SMS baÅŸarÄ±sÄ±z olsa da HTTP yanÄ±tÄ± 200 dÃ¶ner (SMS opsiyonel)
    - CLAUDE.md: randevu iptali SMS'i MVP dÄ±ÅŸÄ± â€” altyapÄ± hazÄ±r, gÃ¶nderim aktif

    Randevu bulunamazsa veya zaten iptal edilmiÅŸse 404 dÃ¶ner.
    """
    # Service: randevuyu iptal et, mÃ¼ÅŸterinin telefon numarasÄ±nÄ± dÃ¶ndÃ¼r
    booking, user_phone = await booking_service.cancel_booking_admin(
        db,
        tenant_id=admin.tenant_id,
        booking_id=booking_id,
    )

    # SMS background task: telefon varsa notification kuyruÄŸuna ekle
    # SMS baÅŸarÄ±sÄ±z olsa bile HTTP yanÄ±tÄ± etkilenmez (CLAUDE.md: non-blocking)
    if user_phone:
        slot_str = booking.slot_time.strftime("%d.%m.%Y %H:%M")
        background_tasks.add_task(
            notification_service.send_sms_task,
            AsyncSessionLocal,                              # background task kendi session'Ä±nÄ± aÃ§ar
            get_sms_provider(),                            # dev: Mock, prod: Twilio
            admin.tenant_id,
            user_phone,
            notification_service.format_booking_cancelled_message(slot_str),
            NotificationMessageType.booking_cancelled,
        )

    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        slot_time=booking.slot_time,
        status=booking.status,
        cancelled_by=booking.cancelled_by,
        created_at=booking.created_at,
    )


@router.post("/admin/bookings/{booking_id}/mark-no-show", response_model=BookingResponse)
async def mark_booking_no_show(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Slot saati gelmis/gecmis confirmed randevuyu no_show olarak isaretler.
    """
    booking = await booking_service.set_booking_no_show_admin(
        db,
        tenant_id=admin.tenant_id,
        booking_id=booking_id,
    )
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        slot_time=booking.slot_time,
        status=booking.status,
        cancelled_by=booking.cancelled_by,
        created_at=booking.created_at,
    )


@router.post("/admin/bookings/{booking_id}/mark-confirmed", response_model=BookingResponse)
async def mark_booking_confirmed(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    no_show randevuyu tekrar confirmed durumuna alir.
    """
    booking = await booking_service.set_booking_confirmed_admin(
        db,
        tenant_id=admin.tenant_id,
        booking_id=booking_id,
    )
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        slot_time=booking.slot_time,
        status=booking.status,
        cancelled_by=booking.cancelled_by,
        created_at=booking.created_at,
    )


# â”€â”€â”€ Admin: Manuel Randevu OluÅŸturma â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post(
    "/admin/bookings",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking_admin(
    body: AdminBookingCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    """
    Admin telefon ile gelen mÃ¼ÅŸteri iÃ§in manuel randevu oluÅŸturur.

    Find-or-create mantÄ±ÄŸÄ±:
    1. body.phone + tenant_id ile User tablosunu ara
    2. User varsa â†’ mevcut user.id ile randevu oluÅŸtur
    3. User yoksa â†’ body.first_name ve body.last_name zorunlu hale gelir;
       yeni User kaydÄ± aÃ§Ä±lÄ±r, ardÄ±ndan randevu oluÅŸturulur

    TÃ¼m booking iÅŸ kurallarÄ± geÃ§erlidir:
    slot_taken, slot_blocked, already_booked_today, slot_in_past vb.
    """
    input_phone = _normalize_phone(body.phone)
    user = None

    # Telefon girilmisse mevcut kullaniciyi ara, bos ise direkt yeni kayit akisina gec.
    if input_phone is not None:
        result = await db.execute(
            select(User).where(
                User.tenant_id == admin.tenant_id,
                User.phone == input_phone,
            )
        )
        user = result.scalar_one_or_none()

    if user is None:
        # KullanÄ±cÄ± sistemde yok â€” yeni kayÄ±t aÃ§Ä±lacak; isim/soyisim zorunlu
        if not body.first_name or not body.last_name:
            # Ä°sim veya soyisim eksik â€” yeni kullanÄ±cÄ± oluÅŸturulamaz
            raise HTTPException(
                422,
                {"error": "missing_user_info",
                 "detail": "Yeni musteri icin first_name ve last_name zorunludur."},
            )

        user_phone = input_phone or _build_placeholder_phone()

        # Yeni kullanÄ±cÄ±yÄ± oluÅŸtur ve kaydet
        user = User(
            tenant_id=admin.tenant_id,
            phone=user_phone,
            first_name=body.first_name,
            last_name=body.last_name,
        )
        db.add(user)
        try:
            await db.flush()  # id'yi almak iÃ§in flush yap â€” commit Ã¶ncesi geÃ§ici commit gibi davranÄ±r
            # flush neden commit deÄŸil?
            # Randevu oluÅŸturma transaction'Ä± aÅŸaÄŸÄ±da create_booking_admin iÃ§inde commit yapÄ±yor.
            # Ã–nce commit edip sonra randevu oluÅŸturursak mÃ¼ÅŸteri aÃ§Ä±lÄ±r ama randevu baÅŸarÄ±sÄ±z olabilir.
            # flush: insert'i yapar ama transaction'Ä± aÃ§Ä±k bÄ±rakÄ±r â€” her ikisi atomik olur.
        except IntegrityError:
            # Race condition: aynÄ± telefon+tenant iÃ§in eÅŸzamanlÄ± iki istek geldi,
            # diÄŸeri Ã¶nce commit etti. Rollback yapÄ±p mevcut kullanÄ±cÄ±yÄ± yeniden al.
            await db.rollback()
            if input_phone is not None:
                result = await db.execute(
                    select(User).where(
                        User.tenant_id == admin.tenant_id,
                        User.phone == input_phone,
                    )
                )
                user = result.scalar_one_or_none()
                if user is None:
                    # Rollback sonrasÄ± yine bulunamadÄ±ysa beklenmedik durum
                    raise HTTPException(500, {"error": "user_creation_failed"})
            else:
                # Telefonsuz placeholder kayitta beklenmedik cakisma.
                raise HTTPException(500, {"error": "user_creation_failed"})

    # AdÄ±m 2: Randevuyu oluÅŸtur (aynÄ± atomik mantÄ±k â€” booking/service.py)
    booking = await booking_service.create_booking_admin(
        db,
        tenant_id=admin.tenant_id,
        user_id=user.id,
        slot_time=body.slot_time,
    )
    return BookingResponse(
        id=booking.id,
        user_id=booking.user_id,
        slot_time=booking.slot_time,
        status=booking.status,
        cancelled_by=booking.cancelled_by,
        created_at=booking.created_at,
    )


