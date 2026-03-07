"""
test_admin_api.py — Admin panel endpoint'leri için otomatik testler.

Test senaryoları (CURSOR_PROMPTS.md ADIM 9):
  1. Dashboard booking listesi doğru dönüyor
  2. Cancelled randevular listede yer alıyor
  3. Boş gün için dashboard (0 randevu)
  4. Manuel randevu: mevcut kullanıcı telefonu ile başarılı
  5. Manuel randevu: yeni kullanıcı için isim/soyisim ile başarılı
  6. Manuel randevu: yeni kullanıcı, isim eksik → 422 missing_user_info
  7. Manuel randevu: yeni kullanıcı, soyisim eksik → 422 missing_user_info

Service fonksiyonları doğrudan test edilir (router bypass).
Mock DB ile gerçek DB bağlantısı gerekmez.
"""

import uuid
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from app.models.enums import BookingStatus, CancelledBy
from app.modules.admin import service as admin_service
from app.modules.schedule.schemas import SlotStatus

TZ = ZoneInfo("Europe/Istanbul")
TEST_TENANT_ID = uuid.uuid4()
TEST_USER_ID = uuid.uuid4()


# ─── Yardımcı Fabrika Fonksiyonlar ───────────────────────────────────────────

def _make_booking(
    slot_dt: datetime,
    user_id: uuid.UUID | None = None,
    status: BookingStatus = BookingStatus.confirmed,
    cancelled_by: CancelledBy | None = None,
) -> SimpleNamespace:
    """Test için Booking benzeri nesne üretir."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        user_id=user_id or TEST_USER_ID,
        slot_time=slot_dt,
        status=status,
        cancelled_by=cancelled_by,
        created_at=datetime.now(TZ),
        updated_at=datetime.now(TZ),
    )


def _make_user(
    user_id: uuid.UUID | None = None,
    phone: str = "+905551234567",
    first_name: str = "Ali",
    last_name: str = "Yılmaz",
) -> SimpleNamespace:
    """Test için User benzeri nesne üretir."""
    return SimpleNamespace(
        id=user_id or TEST_USER_ID,
        tenant_id=TEST_TENANT_ID,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
    )


def _make_db_result(value) -> MagicMock:
    """
    db.execute() dönüş değerini taklit eder.
    scalar_one_or_none() → value döndürür.
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _slot(days_ahead: int = 1, hour: int = 10) -> datetime:
    """Belirli bir gün için slot zamanı üretir (İstanbul timezone'unda)."""
    now = datetime.now(TZ)
    base = datetime(now.year, now.month, now.day, hour, 0, tzinfo=TZ)
    return base + timedelta(days=days_ahead)


def _target_date(days_ahead: int = 1) -> date:
    """Test tarihi: bugünden 'days_ahead' gün sonrası."""
    return (datetime.now(TZ) + timedelta(days=days_ahead)).date()


# ─── get_bookings_by_date mock yardımcısı ─────────────────────────────────────

def _make_mock_db_for_dashboard(rows: list) -> AsyncMock:
    """
    admin_service.get_dashboard için mock DB oturumu oluşturur.
    rows: [(Booking, User), ...] listesi — get_bookings_by_date'den döneceğini simüle eder.

    get_dashboard, booking_service.get_bookings_by_date'i çağırır.
    Bu fonksiyon db.execute().all() kullanır; bu yüzden result.all() mock'u gerekli.
    """
    result = MagicMock()
    result.all.return_value = rows  # result.all() → rows listesi

    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)
    return db


# ─── Dashboard Testleri ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_booking_list_correct():
    """
    Test 1: Günde 3 confirmed randevu varsa booking listesinde 3 kayıt döner.
    Para bilgisi response'da yoktur (bu test para alanı olmadığını da doğrular).
    """
    target = _target_date(1)
    user = _make_user()

    # 3 confirmed randevu oluştur
    bookings = [
        (_make_booking(_slot(1, 9), status=BookingStatus.confirmed), user),
        (_make_booking(_slot(1, 10), status=BookingStatus.confirmed), user),
        (_make_booking(_slot(1, 11), status=BookingStatus.confirmed), user),
    ]

    db = _make_mock_db_for_dashboard(bookings)

    result = await admin_service.get_dashboard(db, TEST_TENANT_ID, target)

    # Toplam randevu sayısı da 3 olmalı
    assert len(result["bookings"]) == 3
    # Para bilgisi döndürülmüyor mu? (CLAUDE.md: ödeme MVP dışı)
    assert "revenue" not in result
    assert "price" not in result
    assert "amount" not in result
    # Tarih doğru mu?
    assert result["date"] == target


@pytest.mark.asyncio
async def test_dashboard_cancelled_not_counted():
    """
    Test 2: Cancelled randevular booking listesinde görünür.
    2 confirmed + 1 cancelled → toplam liste 3 kayıt olmalı.
    """
    target = _target_date(1)
    user = _make_user()

    rows = [
        (_make_booking(_slot(1, 9), status=BookingStatus.confirmed), user),
        (_make_booking(_slot(1, 10), status=BookingStatus.confirmed), user),
        # Bu randevu iptal edilmiş — sayıya dahil olmamalı
        (_make_booking(
            _slot(1, 11),
            status=BookingStatus.cancelled,
            cancelled_by=CancelledBy.admin,
        ), user),
    ]

    db = _make_mock_db_for_dashboard(rows)

    result = await admin_service.get_dashboard(db, TEST_TENANT_ID, target)

    # Toplam randevu listesinde 3 kayıt dönmeli (cancelled de görünür)
    assert len(result["bookings"]) == 3


@pytest.mark.asyncio
async def test_dashboard_empty_day():
    """
    Test 3: Hiç randevu yoksa bookings=[] döner.
    Boş gün hata vermemeli.
    """
    target = _target_date(2)
    db = _make_mock_db_for_dashboard([])  # Boş liste — randevu yok

    result = await admin_service.get_dashboard(db, TEST_TENANT_ID, target)

    assert result["bookings"] == []
    assert result["date"] == target


@pytest.mark.asyncio
async def test_dashboard_booking_has_user_info():
    """
    Test 4: Her randevu item'ında müşteri bilgileri (isim, soyisim, telefon) bulunmalı.
    Admin kimin geldiğini takvimde görmeli.
    """
    target = _target_date(1)
    user = _make_user(first_name="Mehmet", last_name="Demir", phone="+905559876543")
    booking = _make_booking(_slot(1, 9), user_id=user.id)

    db = _make_mock_db_for_dashboard([(booking, user)])

    result = await admin_service.get_dashboard(db, TEST_TENANT_ID, target)

    item = result["bookings"][0]
    # Müşteri bilgileri doğru mu?
    assert item["user_first_name"] == "Mehmet"
    assert item["user_last_name"] == "Demir"
    assert item["user_phone"] == "+905559876543"
    # Slot zamanı doğru mu?
    assert item["slot_time"] == booking.slot_time
    # Status doğru mu?
    assert item["status"] == BookingStatus.confirmed


@pytest.mark.asyncio
async def test_dashboard_all_cancelled_listed():
    """
    Test 5: Günün tüm randevuları cancelled ise listede yine görünmelidir.
    """
    target = _target_date(1)
    user = _make_user()

    rows = [
        (_make_booking(
            _slot(1, 9),
            status=BookingStatus.cancelled,
            cancelled_by=CancelledBy.admin,
        ), user),
        (_make_booking(
            _slot(1, 10),
            status=BookingStatus.cancelled,
            cancelled_by=CancelledBy.admin,
        ), user),
    ]

    db = _make_mock_db_for_dashboard(rows)
    result = await admin_service.get_dashboard(db, TEST_TENANT_ID, target)

    # Liste 2 kayıt içermeli
    assert len(result["bookings"]) == 2



@pytest.mark.asyncio
async def test_overview_birlesik_veri_doner(monkeypatch):
    """
    Test: get_overview tek cagriyla bookings + slots + blocks verisini birlestirir.
    """
    target = _target_date(1)
    user = _make_user(first_name="Ayse", last_name="Kaya", phone="+905551111111")
    booking = _make_booking(_slot(1, 12), status=BookingStatus.confirmed)

    async def fake_get_bookings_by_date(db, tenant_id, target_date):
        return [(booking, user)]

    day_slots = SimpleNamespace(
        is_closed=False,
        slots=[
            SimpleNamespace(
                time="12:00",
                datetime=booking.slot_time,
                end_datetime=booking.slot_time + timedelta(minutes=30),
                status=SlotStatus.booked,
            )
        ],
    )

    async def fake_get_slots_for_date(db, tenant_id, target_date):
        return day_slots

    block = SimpleNamespace(
        id=uuid.uuid4(),
        blocked_at=booking.slot_time + timedelta(hours=1),
        reason="Mola",
    )

    async def fake_get_blocks_for_date(db, tenant_id, target_date):
        return [block]

    monkeypatch.setattr(
        "app.modules.admin.service.booking_service.get_bookings_by_date",
        fake_get_bookings_by_date,
    )
    monkeypatch.setattr(
        "app.modules.admin.service.schedule_service.get_slots_for_date",
        fake_get_slots_for_date,
    )
    monkeypatch.setattr(
        "app.modules.admin.service.schedule_service.get_blocks_for_date",
        fake_get_blocks_for_date,
    )

    result = await admin_service.get_overview(AsyncMock(), TEST_TENANT_ID, target)

    assert result["date"] == target
    assert len(result["bookings"]) == 1
    assert result["bookings"][0]["user_first_name"] == "Ayse"
    assert len(result["slots"]) == 1
    assert result["slots"][0]["status"] == SlotStatus.booked
    assert len(result["blocks"]) == 1
    assert result["blocks"][0]["id"] == block.id

