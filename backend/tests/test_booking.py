"""
test_booking.py — Booking modülü için otomatik testler.

Test senaryoları (CURSOR_PROMPTS.md ADIM 7):
  1. Geçmiş slot → 400 slot_in_past
  2. 14 günden uzak slot → 400 too_far_in_future
  3. Geçersiz slot (berber ayarı yok) → 400 invalid_slot
  4. Kapalı günde slot → 400 invalid_slot
  5. Dolu slot → 409 slot_taken
  6. Bloklu slot → 409 slot_blocked
  7. Aynı gün ikinci randevu → 409 already_booked_today
  8. IntegrityError (eşzamanlı INSERT) → 409 slot_taken
  9. 10 eşzamanlı istek → sadece 1 başarılı, diğerleri 409 (race condition)
 10. Admin iptal → 200, status=cancelled, NotificationLog kaydı
 11. Zaten iptal edilmiş randevuyu tekrar iptal → 404

Servis fonksiyonları doğrudan test edilir (router bypass).
Mock DB ile gerçek DB bağlantısı gerekmez.
"""

import asyncio
import uuid
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.enums import BookingStatus, CancelledBy
from app.modules.booking import service as booking_service

TZ = ZoneInfo("Europe/Istanbul")
TEST_TENANT_ID = uuid.uuid4()
TEST_USER_ID = uuid.uuid4()


# ─── Yardımcı Fabrika Fonksiyonlar ───────────────────────────────────────────

def _make_profile(
    slot_duration_minutes: int = 30,
    work_start: time = time(9, 0),
    work_end: time = time(19, 0),
    weekly_closed_days: list[int] | None = None,
) -> SimpleNamespace:
    """Test için BarberProfile benzeri nesne üretir."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        slot_duration_minutes=slot_duration_minutes,
        work_start_time=work_start,
        work_end_time=work_end,
        weekly_closed_days=weekly_closed_days or [],
    )


def _make_booking(
    slot_dt: datetime,
    user_id: uuid.UUID | None = None,
    status: str = "confirmed",
) -> SimpleNamespace:
    """
    Test için Booking benzeri nesne üretir.
    slot_time timezone-aware olmalı (service _to_utc çağırır).
    """
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        user_id=user_id or TEST_USER_ID,
        slot_time=slot_dt,
        status=(
            BookingStatus.confirmed
            if status == "confirmed"
            else BookingStatus.no_show if status == "no_show" else BookingStatus.cancelled
        ),
        cancelled_by=CancelledBy.admin if status == "cancelled" else None,
        created_at=datetime.now(TZ),
        updated_at=datetime.now(TZ),
    )


def _make_slot_block(blocked_at: datetime) -> SimpleNamespace:
    """Test için SlotBlock benzeri nesne üretir."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        blocked_at=blocked_at,
        reason=None,
    )


def _make_user(user_id: uuid.UUID | None = None) -> SimpleNamespace:
    """Test için User benzeri nesne üretir."""
    return SimpleNamespace(
        id=user_id or TEST_USER_ID,
        tenant_id=TEST_TENANT_ID,
        phone="5551234567",
        first_name="Test",
        last_name="Kullanici",
    )


def _make_db_result(value) -> MagicMock:
    """
    db.execute() dönüş değerini taklit eder.
    scalar_one_or_none() → value döndürür.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_db_scalars_result(values: list) -> MagicMock:
    """
    db.execute() sonucu icin scalars().all() yolunu simule eder.
    Gunluk randevu sayisi gibi coklu kayit okunan sorgularda kullanilir.
    """
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = values
    result.scalars.return_value = scalars_result
    result.scalar_one_or_none.return_value = values[0] if values else None
    return result


def _make_mock_session(*execute_return_values) -> AsyncMock:
    """
    DB session mock'u oluşturur.
    execute_return_values sıralı olarak döndürülür (side_effect listesi).
    add, commit, rollback, refresh MockMock/AsyncMock olarak ayarlanır.
    """
    session = AsyncMock()
    session.add = MagicMock()       # sync — sadece objeyi listeye ekler
    session.commit = AsyncMock()    # async — transaction'ı kapatır
    session.rollback = AsyncMock()  # async — transaction'ı geri alır
    session.refresh = AsyncMock()   # async — objeyi DB'den yeniler

    if not execute_return_values:
        session.execute = AsyncMock(return_value=_make_db_result(None))
    elif len(execute_return_values) == 1:
        session.execute = AsyncMock(return_value=execute_return_values[0])
    else:
        # Birden fazla execute() çağrısı için sıralı dönüş değerleri
        session.execute = AsyncMock(side_effect=list(execute_return_values))

    return session


def _future_slot(days_ahead: int = 1, hour: int = 9) -> datetime:
    """
    Bugünden 'days_ahead' gün sonrası için geçerli bir slot zamanı üretir.
    İstanbul saatiyle saat 09:00 (ya da verilen saat).
    """
    now = datetime.now(TZ)
    base = datetime(now.year, now.month, now.day, hour, 0, tzinfo=TZ)
    return base + timedelta(days=days_ahead)


# ─── Test 1: Geçmiş Slot ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gecmis_slot_400():
    """
    Geçmiş bir slot zamanı ile randevu alınmaya çalışılırsa 400 slot_in_past hatası alınmalı.
    DB sorgusu yapılmadan hata fırlatılır — yani DB mock'una gerek yok.
    """
    # Dün saat 09:00 — kesinlikle geçmişte
    gecmis_slot = _future_slot(days_ahead=-1)

    session = _make_mock_session()

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, gecmis_slot)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "slot_in_past"


# ─── Test 2: 7 Günden Uzak Slot ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_14_gun_otesi_400():
    """
    14 günden daha ileri bir slota randevu alınamaz → 400 too_far_in_future.
    DB sorgusu yapılmadan hata fırlatılır.
    """
    # 15 gün sonrası — izin verilen sınırın dışında
    uzak_slot = _future_slot(days_ahead=15)

    session = _make_mock_session()

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, uzak_slot)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "too_far_in_future"


@pytest.mark.asyncio
async def test_14_gun_sinirinda_slot_too_far_hatasi_vermez():
    """
    14 gun sonrasindaki slot pencere icindedir; too_far_in_future donmemeli.
    Berber ayari olmadigi icin sonraki kuraldan invalid_slot hatasi beklenir.
    """
    sinirdaki_slot = _future_slot(days_ahead=14)

    session = _make_mock_session(
        _make_db_result(None),  # BarberProfile yok -> invalid_slot
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, sinirdaki_slot)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "invalid_slot"


# ─── Test 3: Geçersiz Slot — Berber Ayarı Yok ────────────────────────────────

@pytest.mark.asyncio
async def test_gecersiz_slot_berber_ayari_yok_400():
    """
    Berber henüz çalışma ayarlarını girmemiş (BarberProfile yok) → 400 invalid_slot.
    _validate_slot_in_schedule: BarberProfile None → False döner → hata.
    """
    yarin_slot = _future_slot(days_ahead=1)

    # execute() #1: BarberProfile sorgusu → None (kayıt yok)
    session = _make_mock_session(
        _make_db_result(None),  # BarberProfile bulunamadı
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "invalid_slot"


# ─── Test 4: Geçersiz Slot — Kapalı Gün ─────────────────────────────────────

@pytest.mark.asyncio
async def test_gecersiz_slot_kapali_gun_400():
    """
    DayOverride.is_closed=True olan günde slot alınamaz → 400 invalid_slot.
    """
    yarin_slot = _future_slot(days_ahead=1)

    profile = _make_profile()
    # Yarın kapalı gün olarak işaretlenmiş
    kapali_gun_override = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        date=yarin_slot.date(),
        is_closed=True,
        work_start_time=None,
        work_end_time=None,
    )

    # execute() #1: BarberProfile → var
    # execute() #2: DayOverride → kapali_gun_override (is_closed=True)
    session = _make_mock_session(
        _make_db_result(profile),
        _make_db_result(kapali_gun_override),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "invalid_slot"


@pytest.mark.asyncio
async def test_gecersiz_slot_haftalik_kapali_gun_400():
    """
    Profilde haftalik kapali gun olarak tanimli bir gunde slot alinamaz.
    """
    yarin_slot = _future_slot(days_ahead=1)
    weekly_closed = [yarin_slot.weekday()]
    profile = _make_profile(weekly_closed_days=weekly_closed)

    session = _make_mock_session(
        _make_db_result(profile),  # BarberProfile var ama gun kapali
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "invalid_slot"


# ─── Test 5: Dolu Slot ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dolu_slot_409():
    """
    Bu slotta zaten confirmed randevu var → 409 slot_taken.
    SELECT FOR UPDATE confirmed booking bulursa hata fırlatılır.
    """
    yarin_slot = _future_slot(days_ahead=1)
    mevcut_randevu = _make_booking(yarin_slot)

    profile = _make_profile()

    # execute() #1: BarberProfile → var
    # execute() #2: DayOverride → yok
    # execute() #3: SELECT booking FOR UPDATE → mevcut_randevu bulundu (slot dolu!)
    session = _make_mock_session(
        _make_db_result(profile),
        _make_db_result(None),          # DayOverride yok
        _make_db_result(mevcut_randevu),  # Slot dolu
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "slot_taken"
    # Transaction rollback yapılmalı
    session.rollback.assert_called_once()


# ─── Test 6: Bloklu Slot ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bloklu_slot_409():
    """
    Admin bu slotu bloklamış → 409 slot_blocked.
    SELECT FOR UPDATE slot_block bulursa hata fırlatılır.
    """
    yarin_slot = _future_slot(days_ahead=1)
    blok = _make_slot_block(yarin_slot)

    profile = _make_profile()

    # execute() #1: BarberProfile → var
    # execute() #2: DayOverride → yok
    # execute() #3: SELECT booking FOR UPDATE → yok (slot boş)
    # execute() #4: SELECT slot_block FOR UPDATE → blok var!
    session = _make_mock_session(
        _make_db_result(profile),
        _make_db_result(None),   # DayOverride yok
        _make_db_result(None),   # Booking yok (slot boş)
        _make_db_result(blok),   # Slot bloklu!
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "slot_blocked"
    session.rollback.assert_called_once()


# ─── Test 7: Aynı Gün İkinci Randevu ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_ayni_gun_ikinci_randevu_onay_gerekli_409():
    """
    Kullanici ayni gunde ikinci randevuyu onaysiz almaya calisirsa
    409 additional_booking_confirmation_required donmelidir.
    """
    # Ayni gun farkli slot: sabah 09:00'da randevu var, 10:00'a almak istiyor
    yarin_09 = _future_slot(days_ahead=1, hour=9)
    yarin_10 = _future_slot(days_ahead=1, hour=10)

    # Kullanicinin o gun icin mevcut randevusu
    gun_randevusu = _make_booking(yarin_09, user_id=TEST_USER_ID)

    profile = _make_profile()

    # execute() #1: BarberProfile -> var
    # execute() #2: DayOverride -> yok
    # execute() #3: SELECT booking FOR UPDATE (slot check) -> yok (10:00 bos)
    # execute() #4: SELECT slot_block FOR UPDATE -> yok
    # execute() #5: SELECT booking FOR UPDATE (user day) -> gun randevusu bulundu
    session = _make_mock_session(
        _make_db_result(profile),
        _make_db_result(None),
        _make_db_result(None),
        _make_db_result(None),
        _make_db_scalars_result([gun_randevusu]),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_10)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "additional_booking_confirmation_required"
    assert exc_info.value.detail["current_count"] == 1
    session.rollback.assert_called_once()


# ─── Test 8: IntegrityError → slot_taken ─────────────────────────────────────

@pytest.mark.asyncio
async def test_integrity_error_slot_taken_409():
    """
    Eşzamanlı iki istek aynı slota geldi:
    Her iki istek de SELECT FOR UPDATE'te "boş" gördü,
    ama commit anında unique index ihlali oluştu → 409 slot_taken.

    Bu, race condition durumunda doğru hata döndürüldüğünü test eder.
    """
    yarin_slot = _future_slot(days_ahead=1)
    profile = _make_profile()

    # Tüm SELECT'ler boş döner (her iki concurrent istek de geçiyor)
    # Ama commit'te IntegrityError oluşur (ix_bookings_tenant_slot_confirmed ihlali)
    session = _make_mock_session(
        _make_db_result(profile),  # BarberProfile
        _make_db_result(None),     # DayOverride yok
        _make_db_result(None),     # Booking yok (slot boş)
        _make_db_result(None),     # SlotBlock yok
        _make_db_scalars_result([]),  # User day booking yok
    )

    # commit() IntegrityError fırlatır — slot unique index ihlali
    # ix_bookings_tenant_slot_confirmed: (tenant_id, slot_time) unique WHERE status='confirmed'
    session.commit = AsyncMock(
        side_effect=IntegrityError(
            "INSERT violates unique constraint",
            params={},
            orig=Exception("ix_bookings_tenant_slot_confirmed"),
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "slot_taken"
    # Rollback yapılmış olmalı
    session.rollback.assert_called_once()


# ─── Test 9: IntegrityError → already_booked_today ───────────────────────────

@pytest.mark.asyncio
async def test_ayni_gun_ucuncu_randevu_onayla_basarili():
    """
    Kullanici ayni gunde 2 aktif randevusu varken, ek onay vererek 3. randevuyu alabilir.
    """
    yarin_slot = _future_slot(days_ahead=1, hour=11)
    yarin_09 = _future_slot(days_ahead=1, hour=9)
    yarin_10 = _future_slot(days_ahead=1, hour=10)
    profile = _make_profile()
    day_bookings = [
        _make_booking(yarin_09, user_id=TEST_USER_ID),
        _make_booking(yarin_10, user_id=TEST_USER_ID),
    ]

    session = _make_mock_session(
        _make_db_result(profile),
        _make_db_result(None),
        _make_db_result(None),
        _make_db_result(None),
        _make_db_scalars_result(day_bookings),
    )

    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(TZ)
        obj.updated_at = datetime.now(TZ)
        obj.cancelled_by = None

    session.refresh = mock_refresh

    booking = await booking_service.create_booking(
        session,
        TEST_TENANT_ID,
        TEST_USER_ID,
        yarin_slot,
        confirm_additional_same_day=True,
    )

    assert booking.status == BookingStatus.confirmed
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_ayni_gun_dorduncu_randevu_409():
    """
    Kullanici ayni gunde 3 confirmed randevusu varken 4. randevuyu alamaz.
    """
    yarin_slot = _future_slot(days_ahead=1, hour=12)
    profile = _make_profile()
    day_bookings = [
        _make_booking(_future_slot(days_ahead=1, hour=9), user_id=TEST_USER_ID),
        _make_booking(_future_slot(days_ahead=1, hour=10), user_id=TEST_USER_ID),
        _make_booking(_future_slot(days_ahead=1, hour=11), user_id=TEST_USER_ID),
    ]

    session = _make_mock_session(
        _make_db_result(profile),
        _make_db_result(None),
        _make_db_result(None),
        _make_db_result(None),
        _make_db_scalars_result(day_bookings),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.create_booking(
            session,
            TEST_TENANT_ID,
            TEST_USER_ID,
            yarin_slot,
            confirm_additional_same_day=True,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "daily_booking_limit_exceeded"
    assert exc_info.value.detail["current_count"] == 3
    session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_basarili_randevu_olusturma():
    """
    Geçerli slot, boş takvim, ilk randevu → 201 + booking nesnesi döner.
    Tüm kontroller geçilir, INSERT başarılı, commit çağrılır.
    """
    yarin_slot = _future_slot(days_ahead=1)
    profile = _make_profile()

    # Tüm SELECT'ler boş döner (slot müsait)
    session = _make_mock_session(
        _make_db_result(profile),  # BarberProfile: var
        _make_db_result(None),     # DayOverride: yok
        _make_db_result(None),     # Booking FOR UPDATE: yok (slot boş)
        _make_db_result(None),     # SlotBlock FOR UPDATE: yok
        _make_db_scalars_result([]),  # User day booking FOR UPDATE: yok
    )

    # refresh: oluşturulan booking nesnesine id ve created_at atar
    async def mock_refresh(obj):
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(TZ)
        obj.updated_at = datetime.now(TZ)
        obj.cancelled_by = None

    session.refresh = mock_refresh

    booking = await booking_service.create_booking(
        session, TEST_TENANT_ID, TEST_USER_ID, yarin_slot
    )

    # Commit çağrılmış olmalı
    session.commit.assert_called_once()
    session.add.assert_called_once()
    assert booking.tenant_id == TEST_TENANT_ID
    assert booking.user_id == TEST_USER_ID
    assert booking.status == BookingStatus.confirmed
    assert booking.cancelled_by is None


@pytest.mark.asyncio
async def test_admin_iptal_gecmis_randevu_409():
    """
    Slot saati gelmis/gecmis randevu admin tarafindan iptal edilemez.
    """
    booking_id = uuid.uuid4()
    gecmis_slot = _future_slot(days_ahead=-1)
    confirmed_booking = _make_booking(gecmis_slot, status="confirmed")
    confirmed_booking.id = booking_id

    session = _make_mock_session(
        _make_db_result(confirmed_booking),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.cancel_booking_admin(session, TEST_TENANT_ID, booking_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "booking_cancellation_window_passed"


@pytest.mark.asyncio
async def test_kullanici_iptal_200():
    """
    Kullanici kendi confirmed ve gelecekteki randevusunu iptal edebilir.
    cancelled_by=user olmalidir.
    """
    booking_id = uuid.uuid4()
    yarin_slot = _future_slot(days_ahead=1, hour=10)
    confirmed_booking = _make_booking(yarin_slot, user_id=TEST_USER_ID, status="confirmed")
    confirmed_booking.id = booking_id

    session = _make_mock_session(
        _make_db_result(confirmed_booking),
    )

    booking = await booking_service.cancel_booking_user(
        session,
        TEST_TENANT_ID,
        TEST_USER_ID,
        booking_id,
    )

    assert booking.status == BookingStatus.cancelled
    assert booking.cancelled_by == CancelledBy.user
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_kullanici_baskasinin_randevusunu_iptal_edemez_404():
    """
    Kullanici kendi olmayan booking kaydini iptal edemez.
    """
    booking_id = uuid.uuid4()
    yarin_slot = _future_slot(days_ahead=1, hour=11)
    baska_user_booking = _make_booking(yarin_slot, user_id=uuid.uuid4(), status="confirmed")
    baska_user_booking.id = booking_id

    session = _make_mock_session(
        _make_db_result(baska_user_booking),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.cancel_booking_user(
            session,
            TEST_TENANT_ID,
            TEST_USER_ID,
            booking_id,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"] == "booking_not_found"


@pytest.mark.asyncio
async def test_kullanici_iptal_15_dakikadan_az_kaldiysa_409():
    """
    Kullanici, slot saatine 15 dakikadan az kaldiysa iptal edemez.
    """
    booking_id = uuid.uuid4()
    yakin_slot = datetime.now(TZ) + timedelta(minutes=10)
    confirmed_booking = _make_booking(yakin_slot, user_id=TEST_USER_ID, status="confirmed")
    confirmed_booking.id = booking_id

    session = _make_mock_session(
        _make_db_result(confirmed_booking),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.cancel_booking_user(
            session,
            TEST_TENANT_ID,
            TEST_USER_ID,
            booking_id,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "booking_cancellation_window_passed"


@pytest.mark.asyncio
async def test_admin_mark_no_show_ve_confirmed_donus():
    """
    Gecmis confirmed randevu no_show yapilabilir ve tekrar confirmed'e donebilir.
    """
    booking_id = uuid.uuid4()
    gecmis_slot = _future_slot(days_ahead=-1)
    confirmed_booking = _make_booking(gecmis_slot, status="confirmed")
    confirmed_booking.id = booking_id

    session_to_no_show = _make_mock_session(
        _make_db_result(confirmed_booking),
    )
    booking_after_no_show = await booking_service.set_booking_no_show_admin(
        session_to_no_show, TEST_TENANT_ID, booking_id
    )
    assert booking_after_no_show.status == BookingStatus.no_show
    assert booking_after_no_show.cancelled_by is None
    session_to_no_show.commit.assert_called_once()

    session_to_confirmed = _make_mock_session(
        _make_db_result(booking_after_no_show),
    )
    booking_after_confirmed = await booking_service.set_booking_confirmed_admin(
        session_to_confirmed, TEST_TENANT_ID, booking_id
    )
    assert booking_after_confirmed.status == BookingStatus.confirmed
    assert booking_after_confirmed.cancelled_by is None
    session_to_confirmed.commit.assert_called_once()


@pytest.mark.asyncio
async def test_admin_mark_no_show_future_409():
    """
    no_show isaretleme sadece slot saati gelmis/gecmis randevularda yapilabilir.
    """
    booking_id = uuid.uuid4()
    gelecek_slot = _future_slot(days_ahead=1)
    confirmed_booking = _make_booking(gelecek_slot, status="confirmed")
    confirmed_booking.id = booking_id

    session = _make_mock_session(
        _make_db_result(confirmed_booking),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.set_booking_no_show_admin(session, TEST_TENANT_ID, booking_id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error"] == "booking_not_started"


# ─── Test 11: Admin İptal ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_iptal_200():
    """
    Admin randevuyu iptal eder:
    - (booking, user_phone) tuple döner
    - booking.status='cancelled', cancelled_by='admin' olmalı
    - user_phone: notification background task için telefon numarası
    - Commit çağrılmalı

    Not: NotificationLog artık booking/service.py'de oluşturulmuyor.
    notification/service.py'nin send_sms_task() background task'ı oluşturuyor.
    Bu sorumluluk ayrımı (ADIM 8): booking servisi sadece iptali yapar,
    notification servisi SMS + log işini yapar.
    """
    booking_id = uuid.uuid4()
    yarin_slot = _future_slot(days_ahead=1)

    confirmed_booking = _make_booking(yarin_slot)
    confirmed_booking.id = booking_id

    user = _make_user()

    # execute() #1: Booking sorgula
    # execute() #2: User sorgula (telefon için)
    session = _make_mock_session(
        _make_db_result(confirmed_booking),  # Booking bulundu
        _make_db_result(user),               # User bulundu (telefon için)
    )

    # Service artık (booking, user_phone) tuple döndürüyor
    booking, user_phone = await booking_service.cancel_booking_admin(
        session, TEST_TENANT_ID, booking_id
    )

    # Randevu iptal edilmiş olmalı
    assert booking.status == BookingStatus.cancelled
    assert booking.cancelled_by == CancelledBy.admin

    # user_phone: notification background task için döndürülmüş olmalı
    assert user_phone == user.phone

    # NotificationLog artık bu service'de oluşturulmuyor — add() çağrılmamış olmalı
    session.add.assert_not_called()

    # Commit çağrılmış olmalı
    session.commit.assert_called_once()


# ─── Test 12: Zaten İptal Edilmiş Randevu ────────────────────────────────────

@pytest.mark.asyncio
async def test_zaten_iptal_edilmis_randevu_404():
    """
    Zaten iptal edilmiş randevuyu tekrar iptal etmeye çalışmak → 404.
    """
    booking_id = uuid.uuid4()
    yarin_slot = _future_slot(days_ahead=1)

    # status=cancelled — zaten iptal edilmiş
    iptal_randevu = _make_booking(yarin_slot, status="cancelled")
    iptal_randevu.id = booking_id

    session = _make_mock_session(
        _make_db_result(iptal_randevu),
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.cancel_booking_admin(session, TEST_TENANT_ID, booking_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"] == "booking_not_found"


# ─── Test 13: Bulunamayan Randevu İptal ──────────────────────────────────────

@pytest.mark.asyncio
async def test_bulunamayan_randevu_iptal_404():
    """
    Var olmayan booking_id ile iptal → 404 booking_not_found.
    """
    session = _make_mock_session(
        _make_db_result(None),  # Randevu bulunamadı
    )

    with pytest.raises(HTTPException) as exc_info:
        await booking_service.cancel_booking_admin(session, TEST_TENANT_ID, uuid.uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["error"] == "booking_not_found"


# ─── Test 14: Kullanıcı Randevu Listesi ──────────────────────────────────────

@pytest.mark.asyncio
async def test_kullanici_randevu_listesi():
    """
    Kullanıcının randevuları listelenir — her iki status (confirmed/cancelled) dahil.
    """
    yarin_slot = _future_slot(days_ahead=1)
    randevu1 = _make_booking(yarin_slot, status="confirmed")
    randevu2 = _make_booking(_future_slot(days_ahead=2), status="cancelled")

    # scalars().all() çağrısını simüle et
    scalars_result = MagicMock()
    scalars_result.all.return_value = [randevu1, randevu2]
    list_result = MagicMock()
    list_result.scalars.return_value = scalars_result

    session = AsyncMock()
    session.execute = AsyncMock(return_value=list_result)

    bookings = await booking_service.get_user_bookings(session, TEST_TENANT_ID, TEST_USER_ID)

    assert len(bookings) == 2
    assert bookings[0].status == BookingStatus.confirmed
    assert bookings[1].status == BookingStatus.cancelled


# ─── Test 15: Race Condition — 10 Eşzamanlı İstek ───────────────────────────

@pytest.mark.asyncio
async def test_race_condition_10_eslik_istek():
    """
    10 eşzamanlı randevu isteği aynı slota gönderilir.
    Sadece 1 tanesi başarılı olmalı (commit başarılı),
    diğer 9'u IntegrityError almalı ve 409 slot_taken dönmeli.

    Mock stratejisi:
    - İlk commit çağrısı başarılı
    - Sonraki commit çağrıları IntegrityError fırlatır (eşzamanlı INSERT simülasyonu)

    Bu test, service katmanının:
    1. IntegrityError'u doğru yakalamasını
    2. 10 concurrent istekten yalnızca 1'inin başarılı olmasını
    doğrular.
    """
    yarin_slot = _future_slot(days_ahead=1)
    profile = _make_profile()

    # commit sayacı: ilk commit başarılı, diğerleri IntegrityError
    commit_calls: list[int] = [0]  # mutable container — nonlocal yerine

    def make_race_session() -> AsyncMock:
        """
        Her request için bağımsız mock session oluşturur.
        Tüm sessionlar aynı commit_calls sayacını paylaşır.
        """
        session = AsyncMock()
        session.add = MagicMock()
        session.rollback = AsyncMock()

        # Tüm SELECT'ler: slot boş, blok yok, berber ayarı var
        session.execute = AsyncMock(side_effect=[
            _make_db_result(profile),  # BarberProfile: var
            _make_db_result(None),     # DayOverride: yok
            _make_db_result(None),     # Booking FOR UPDATE: boş
            _make_db_result(None),     # SlotBlock FOR UPDATE: yok
            _make_db_scalars_result([]),  # User day booking FOR UPDATE: yok
        ])

        async def mock_commit():
            # commit_calls[0]: kaç kez commit denendi
            # İlk commit başarılı; sonrakiler eşzamanlı INSERT simülasyonu olarak hata verir
            commit_calls[0] += 1
            if commit_calls[0] > 1:
                raise IntegrityError(
                    "INSERT violates unique constraint ix_bookings_tenant_slot_confirmed",
                    params={},
                    orig=Exception("ix_bookings_tenant_slot_confirmed"),
                )
            # İlk commit başarılı — session.refresh() için booking'i hazırla

        session.commit = mock_commit

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(TZ)
            obj.cancelled_by = None

        session.refresh = mock_refresh

        return session

    # 10 eşzamanlı create_booking çağrısı — asyncio.gather ile
    tasks = [
        booking_service.create_booking(
            make_race_session(),
            TEST_TENANT_ID,
            TEST_USER_ID,
            yarin_slot,
        )
        for _ in range(10)
    ]

    # return_exceptions=True: exception'lar da sonuç olarak toplanır
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Başarılı olanlar: HTTPException değil (booking nesnesi döndürüldü)
    success_results = [r for r in results if not isinstance(r, HTTPException)]
    # 409 dönenler: HTTPException + status_code=409
    conflict_results = [
        r for r in results
        if isinstance(r, HTTPException) and r.status_code == 409
    ]

    # Tam olarak 1 başarılı, 9 çakışma olmalı (CURSOR_PROMPTS.md ADIM 7 kuralı)
    assert len(success_results) == 1, (
        f"Beklenen: 1 başarılı istek, alınan: {len(success_results)}"
    )
    assert len(conflict_results) == 9, (
        f"Beklenen: 9 çakışma hatası, alınan: {len(conflict_results)}"
    )

    # Başarılı sonucun doğru status'u olduğunu kontrol et
    successful_booking = success_results[0]
    assert successful_booking.status == BookingStatus.confirmed

    # Tüm çakışma hatalarının slot_taken olduğunu kontrol et
    for conflict in conflict_results:
        assert conflict.detail["error"] == "slot_taken"

