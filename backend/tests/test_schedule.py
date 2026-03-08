"""
test_schedule.py — Slot hesaplama motoru için otomatik testler.

Test senaryoları (CURSOR_PROMPTS.md ADIM 6):
  1. Normal gün: 09:00-19:00, 30dk → 20 slot
  2. DayOverride ile farklı saatler (10:00-14:00, 30dk → 8 slot)
  3. Kapalı günde (is_closed=True) boş liste
  4. Bloklu slot → "blocked" status
  5. Confirmed booking olan slot → "booked" status
  6. Geçmiş slot → "past" status
  7. Randevusu olan slotu kapatmak → 409 + booking_id

Tüm testler service katmanını doğrudan çağırır (router bypass).
DB mock'u ile gerçek bağlantı gerekmez.
'now' parametresi ile saat kontrolü sağlanır.
"""

import uuid
from datetime import date, datetime, time, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from app.modules.schedule import service as schedule_service
from app.modules.schedule.schemas import SlotStatus

TZ = ZoneInfo("Europe/Istanbul")
TEST_TENANT_ID = uuid.uuid4()


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


def _make_override(
    target_date: date,
    is_closed: bool = False,
    start: time | None = None,
    end: time | None = None,
    slot_duration_minutes: int | None = None,
) -> SimpleNamespace:
    """Test için DayOverride benzeri nesne üretir."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        date=target_date,
        is_closed=is_closed,
        work_start_time=start,
        work_end_time=end,
        slot_duration_minutes=slot_duration_minutes,
    )


def _make_booking(slot_dt: datetime) -> SimpleNamespace:
    """
    Test için Booking benzeri nesne üretir.
    slot_time timezone-aware olmalı (service _to_utc çağırır).
    """
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        slot_time=slot_dt,
        status="confirmed",
    )


def _make_block(blocked_at: datetime) -> SimpleNamespace:
    """Test için SlotBlock benzeri nesne üretir."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        blocked_at=blocked_at,
        reason=None,
    )


def _make_scalars_result(items: list) -> MagicMock:
    """
    db.execute().scalars().all() zincirini taklit eder.
    Liste döndüren sorgu sonucu için kullanılır (bookings, blocks gibi).
    """
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars_mock
    return result


def _make_scalar_result(value) -> MagicMock:
    """
    db.execute().scalar_one_or_none() zincirini taklit eder.
    Tekil kayıt döndüren sorgu sonucu için kullanılır (profile, override).
    """
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_mock_session(*execute_returns) -> AsyncMock:
    """
    DB session mock'u oluşturur.
    execute_returns sıralı olarak döndürülür.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()

    if len(execute_returns) == 1:
        session.execute = AsyncMock(return_value=execute_returns[0])
    else:
        session.execute = AsyncMock(side_effect=list(execute_returns))

    return session


# Sabit test tarihi ve "şimdiki zaman" — testler deterministik olsun
TEST_DATE = date(2026, 6, 15)   # Gelecekte bir tarih — slotlar "past" olmasın
TEST_NOW  = datetime(2026, 6, 15, 8, 0, tzinfo=TZ)  # Saat 08:00 → tüm slotlar ileride


# ─── Testler ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_normal_gun_dogru_slot_sayisi():
    """
    09:00-19:00, 30dk slot süresi → 20 slot olmalı.
    Hesaplama: (19:00 - 09:00) = 600 dk / 30 dk = 20 slot.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(19, 0))

    session = _make_mock_session(
        _make_scalar_result(profile),   # 1. execute: BarberProfile
        _make_scalar_result(None),      # 2. execute: DayOverride (yok)
        _make_scalars_result([]),       # 3. execute: Bookings (boş)
        _make_scalars_result([]),       # 4. execute: SlotBlocks (boş)
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    assert result.is_closed is False
    assert len(result.slots) == 20
    # İlk slot 09:00 olmalı
    assert result.slots[0].time == "09:00"
    # Son slot 18:30 olmalı (18:30 + 30dk = 19:00 ≤ 19:00)
    assert result.slots[-1].time == "18:30"
    # Tüm slotlar "available" — ne booking ne block var
    assert all(s.status == SlotStatus.available for s in result.slots)


@pytest.mark.asyncio
async def test_day_override_ile_farkli_saatler():
    """
    DayOverride: 10:00-14:00, 30dk → 8 slot olmalı.
    Normal profil 09:00-19:00 olsa da override geçerli.
    Hesaplama: (14:00 - 10:00) = 240 dk / 30 dk = 8 slot.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(19, 0))
    override = _make_override(TEST_DATE, is_closed=False, start=time(10, 0), end=time(14, 0))

    session = _make_mock_session(
        _make_scalar_result(profile),   # 1. execute: BarberProfile
        _make_scalar_result(override),  # 2. execute: DayOverride (var)
        _make_scalars_result([]),       # 3. execute: Bookings
        _make_scalars_result([]),       # 4. execute: SlotBlocks
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    assert result.is_closed is False
    assert len(result.slots) == 8
    assert result.slots[0].time == "10:00"
    assert result.slots[-1].time == "13:30"


@pytest.mark.asyncio
async def test_day_override_ile_ozel_slot_suresi():
    """
    DayOverride icinde ozel slot suresi verilirse profildeki sureyi ezer.
    10:00-14:00 + 20dk => 12 slot.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(19, 0))
    override = _make_override(
        TEST_DATE,
        is_closed=False,
        start=time(10, 0),
        end=time(14, 0),
        slot_duration_minutes=20,
    )

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(override),
        _make_scalars_result([]),
        _make_scalars_result([]),
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    assert result.is_closed is False
    assert len(result.slots) == 12
    assert result.slots[0].time == "10:00"
    assert result.slots[-1].time == "13:40"


@pytest.mark.asyncio
async def test_genel_ayar_bitis_0000_olunca_son_slot_2330_olur():
    """
    Genel ayarda bitis 00:00 ise gun sonu (24:00) kabul edilir.
    30dk surede 23:00 ve 23:30 slotlari olusmalidir.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(23, 0), work_end=time(0, 0))
    now_22_30 = datetime(2026, 6, 15, 22, 30, tzinfo=TZ)

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(None),
        _make_scalars_result([]),
        _make_scalars_result([]),
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=now_22_30
    )

    assert result.is_closed is False
    assert [slot.time for slot in result.slots] == ["23:00", "23:30"]


@pytest.mark.asyncio
async def test_ozel_gun_bitis_0000_olunca_son_slot_2330_olur():
    """
    Ozel gunde bitis 00:00 ise gun sonu (24:00) kabul edilir.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(19, 0))
    override = _make_override(
        TEST_DATE,
        is_closed=False,
        start=time(23, 0),
        end=time(0, 0),
        slot_duration_minutes=30,
    )
    now_22_30 = datetime(2026, 6, 15, 22, 30, tzinfo=TZ)

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(override),
        _make_scalars_result([]),
        _make_scalars_result([]),
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=now_22_30
    )

    assert result.is_closed is False
    assert [slot.time for slot in result.slots] == ["23:00", "23:30"]


@pytest.mark.asyncio
async def test_kapali_gunde_bos_liste():
    """
    DayOverride is_closed=True → o gün hiç slot dönmemeli.
    is_closed=True ise profil saatlerine bakılmaz.
    """
    profile = _make_profile()
    override = _make_override(TEST_DATE, is_closed=True)

    session = _make_mock_session(
        _make_scalar_result(profile),   # 1. execute: BarberProfile
        _make_scalar_result(override),  # 2. execute: DayOverride (kapalı)
        # 3. ve 4. execute çağrılmaz — is_closed=True erken return yapar
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    assert result.is_closed is True
    assert result.slots == []


@pytest.mark.asyncio
async def test_haftalik_kapali_gunde_bos_liste():
    """
    Profilde haftalik kapali gun olarak tanimli gunde slot olusturulmaz.
    DayOverride olmasa bile is_closed=True ve slots=[] donmelidir.
    """
    # TEST_DATE = 2026-06-15 Pazartesi -> weekday=0
    profile = _make_profile(weekly_closed_days=[0])

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(None),
        _make_scalars_result([]),
        _make_scalars_result([]),
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    assert result.is_closed is True
    assert result.slots == []


@pytest.mark.asyncio
async def test_bloklu_slot_blocked_status():
    """
    Admin'in kapattığı slot → status='blocked' olmalı.
    Diğer slotlar etkilenmemeli.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(10, 30))
    # 09:00 slotunu blokla
    blocked_dt = datetime(2026, 6, 15, 9, 0, tzinfo=TZ)
    block = _make_block(blocked_dt)

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(None),
        _make_scalars_result([]),           # Bookings yok
        _make_scalars_result([block]),      # 09:00 slotu bloklu
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    # 09:00-10:30, 30dk → 3 slot: 09:00, 09:30, 10:00
    assert len(result.slots) == 3
    slot_09_00 = next(s for s in result.slots if s.time == "09:00")
    slot_09_30 = next(s for s in result.slots if s.time == "09:30")

    assert slot_09_00.status == SlotStatus.blocked   # Kapatıldı
    assert slot_09_30.status == SlotStatus.available  # Etkilenmedi


@pytest.mark.asyncio
async def test_dolu_slot_booked_status():
    """
    Confirmed randevu olan slot → status='booked' olmalı.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(10, 30))
    # 09:30 slotuna randevu var
    booked_dt = datetime(2026, 6, 15, 9, 30, tzinfo=TZ)
    booking = _make_booking(booked_dt)

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(None),
        _make_scalars_result([booking]),    # 09:30 dolu
        _make_scalars_result([]),
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=TEST_NOW
    )

    slot_09_00 = next(s for s in result.slots if s.time == "09:00")
    slot_09_30 = next(s for s in result.slots if s.time == "09:30")

    assert slot_09_30.status == SlotStatus.booked     # Randevu var
    assert slot_09_00.status == SlotStatus.available  # Randevu yok


@pytest.mark.asyncio
async def test_gecmis_slot_past_status():
    """
    Saat now'dan önce olan slot → status='past' olmalı.
    'now' = 10:00 olarak ayarlandığında 09:00 ve 09:30 slotları past olmalı.
    """
    profile = _make_profile(slot_duration_minutes=30, work_start=time(9, 0), work_end=time(11, 30))
    # now = 10:00 → 09:00 ve 09:30 past, 10:00 ve 10:30 ve 11:00 available
    now_10 = datetime(2026, 6, 15, 10, 0, tzinfo=TZ)

    session = _make_mock_session(
        _make_scalar_result(profile),
        _make_scalar_result(None),
        _make_scalars_result([]),
        _make_scalars_result([]),
    )

    result = await schedule_service.get_slots_for_date(
        session, TEST_TENANT_ID, TEST_DATE, now=now_10
    )

    # 09:00-11:30, 30dk → 5 slot: 09:00, 09:30, 10:00, 10:30, 11:00
    assert len(result.slots) == 5

    slot_09_00 = next(s for s in result.slots if s.time == "09:00")
    slot_09_30 = next(s for s in result.slots if s.time == "09:30")
    slot_10_00 = next(s for s in result.slots if s.time == "10:00")
    slot_10_30 = next(s for s in result.slots if s.time == "10:30")

    # now = 10:00 → slot_time <= now ise past
    assert slot_09_00.status == SlotStatus.past       # 09:00 <= 10:00 → past
    assert slot_09_30.status == SlotStatus.past       # 09:30 <= 10:00 → past
    assert slot_10_00.status == SlotStatus.past       # 10:00 <= 10:00 → past (tam eşit de geçmiş)
    assert slot_10_30.status == SlotStatus.available  # 10:30 > 10:00 → available


@pytest.mark.asyncio
async def test_randevulu_slotu_kapatmak_409():
    """
    Confirmed randevusu olan bir slotu bloklamak → 409 + booking_id döndürmeli.
    Admin önce randevuyu iptal etmeli (ADIM 7), ardından slotu kapatabilir.
    """
    from fastapi import HTTPException

    slot_dt = datetime(2026, 6, 15, 10, 0, tzinfo=TZ)
    existing_booking = _make_booking(slot_dt)

    # İlk execute: booking var mı sorgusu → booking döndür
    session = _make_mock_session(
        _make_scalar_result(existing_booking)
    )

    with pytest.raises(HTTPException) as exc_info:
        await schedule_service.block_slot(session, TEST_TENANT_ID, slot_dt)

    # 409 Conflict fırlatılmalı
    assert exc_info.value.status_code == 409
    error_detail = exc_info.value.detail
    assert error_detail["error"] == "slot_has_booking"
    # booking_id döndürülmeli — frontend randevuyu bulmak için kullanır
    assert error_detail["booking_id"] == str(existing_booking.id)
