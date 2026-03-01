"""
test_notification.py — Notification modülü için otomatik testler.

Test senaryoları (CURSOR_PROMPTS.md ADIM 8):
  1. Mock provider başarılı → NotificationLog status='sent', provider_response dolu
  2. Mock provider exception fırlatır → NotificationLog status='failed', exception dışarı çıkmaz
  3. DB session açılamaz → exception yutulur, uygulama çökmez
  4. OTP mesaj formatı doğru string üretiyor
  5. Randevu iptal mesaj formatı doğru string üretiyor

service.send_sms_task() doğrudan test edilir (router bypass).
Mock DB factory ve mock provider inject edilir — gerçek bağlantı gerekmez.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from app.models.enums import NotificationMessageType, NotificationStatus
from app.modules.notification import service as notification_service
from app.modules.notification.provider import MockProvider, SMSProvider

TZ = ZoneInfo("Europe/Istanbul")
TEST_TENANT_ID = uuid.uuid4()


# ─── Yardımcı Fabrika Fonksiyonlar ───────────────────────────────────────────

def _make_mock_db_session(captured: dict) -> AsyncMock:
    """
    DB session mock'u oluşturur.

    captured: servis tarafından oluşturulan gerçek NotificationLog nesnesini yakalar.
    Neden gerekli?
    send_sms_task() fonksiyonu kendi içinde yeni bir NotificationLog objesi oluşturur.
    Test, bu objeye erişmek için refresh() çağrısını kullanır:
    refresh(obj) çağrıldığında 'captured["log"] = obj' ile nesne yakalanır.
    Sonrasında test, captured["log"].status üzerinden kontrol yapar.

    Bu yaklaşım dependency injection yerine "spy" (gözetleme) paternidir.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def mock_refresh(obj):
        # Servisin oluşturduğu gerçek NotificationLog nesnesini kaydet
        obj.id = uuid.uuid4()
        obj.created_at = datetime.now(TZ)
        captured["log"] = obj  # Test bu referans üzerinden kontrol yapar

    session.refresh = mock_refresh
    return session


def _make_mock_db_factory(session: AsyncMock):
    """
    AsyncSessionLocal benzeri async context manager factory üretir.
    'async with db_factory() as db:' kalıbını destekler.
    """
    @asynccontextmanager
    async def factory():
        yield session

    return factory


# ─── Test 1: Başarılı SMS Gönderimi ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_sms_gonderim_basarili_sent():
    """
    Mock provider SMS göndermeyi başarıyor:
    - NotificationLog status='sent' olmalı
    - provider_response dolu olmalı
    - DB commit çağrılmış olmalı (2 kez: pending + sent)
    """
    captured: dict = {}  # Servisin oluşturduğu NotificationLog nesnesi burada yakalanır
    session = _make_mock_db_session(captured)
    db_factory = _make_mock_db_factory(session)

    # Mock provider: başarılı gönderim simülasyonu
    mock_provider = AsyncMock(spec=SMSProvider)
    mock_provider.send_sms = AsyncMock(
        return_value={"sid": "SM123abc", "status": "queued", "to": "+905551234567"}
    )

    await notification_service.send_sms_task(
        db_factory=db_factory,
        provider=mock_provider,
        tenant_id=TEST_TENANT_ID,
        recipient_phone="5551234567",
        message="Randevu doğrulama kodunuz: 123456",
        message_type=NotificationMessageType.otp,
    )

    # SMS gönderim çağrısı yapılmış olmalı
    mock_provider.send_sms.assert_called_once_with(
        "5551234567",
        "Randevu doğrulama kodunuz: 123456",
    )

    # refresh() çağrısı ile yakalanan gerçek NotificationLog nesnesi
    log = captured["log"]
    assert log is not None

    # NotificationLog status='sent' olarak güncellenmiş olmalı
    assert log.status == NotificationStatus.sent

    # provider_response kaydedilmiş olmalı
    assert log.provider_response is not None
    assert log.provider_response.get("sid") == "SM123abc"

    # commit() iki kez çağrılmalı:
    # 1. pending kaydı oluştururken, 2. sent olarak güncellerken
    assert session.commit.await_count == 2


# ─── Test 2: SMS Gönderimi Başarısız ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_sms_gonderim_basarisiz_failed():
    """
    Mock provider exception fırlatır:
    - NotificationLog status='failed' olmalı
    - provider_response hata mesajını içermeli
    - Exception send_sms_task dışına ÇIKMAMALI (uygulama çökmez)
    - DB commit çağrılmış olmalı (2 kez: pending + failed)
    """
    captured: dict = {}
    session = _make_mock_db_session(captured)
    db_factory = _make_mock_db_factory(session)

    # Mock provider: hata fırlatır
    mock_provider = AsyncMock(spec=SMSProvider)
    mock_provider.send_sms = AsyncMock(
        side_effect=Exception("Twilio connection error: timeout")
    )

    # send_sms_task exception fırlatmamalı — uygulamayı çökmemeyi test ediyoruz
    await notification_service.send_sms_task(
        db_factory=db_factory,
        provider=mock_provider,
        tenant_id=TEST_TENANT_ID,
        recipient_phone="5551234567",
        message="Randevu doğrulama kodunuz: 654321",
        message_type=NotificationMessageType.otp,
    )

    # refresh() ile yakalanan gerçek NotificationLog nesnesi
    log = captured["log"]
    assert log is not None

    # NotificationLog status='failed' olarak güncellenmiş olmalı
    assert log.status == NotificationStatus.failed

    # provider_response hata mesajını içermeli
    assert log.provider_response is not None
    assert "error" in log.provider_response
    assert "Twilio connection error" in log.provider_response["error"]

    # commit() iki kez çağrılmalı: pending + failed
    assert session.commit.await_count == 2


# ─── Test 3: DB Session Açılamıyor ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_db_session_acilamiyor_uygulama_cokmiyor():
    """
    DB factory hata fırlatır (örn: DB bağlantısı yok):
    - send_sms_task exception dışarıya ÇIKMAMALI
    - Uygulama çalışmaya devam eder

    Bu, SMS'in opsiyonel olduğunu doğrular — DB bağlantısı yoksa bile
    ana uygulama çökmez (CLAUDE.md: hata toleranslı olmalı).
    """
    mock_provider = AsyncMock(spec=SMSProvider)

    # DB factory exception fırlatır — session açılamıyor
    @asynccontextmanager
    async def broken_db_factory():
        raise ConnectionError("DB bağlantısı yok")
        yield  # noqa: unreachable — context manager için gerekli

    # Exception dışarıya çıkmamalı
    await notification_service.send_sms_task(
        db_factory=broken_db_factory,
        provider=mock_provider,
        tenant_id=TEST_TENANT_ID,
        recipient_phone="5551234567",
        message="test mesajı",
        message_type=NotificationMessageType.otp,
    )

    # Uygulama bu noktaya ulaşabilmeli — exception yutuldu
    mock_provider.send_sms.assert_not_called()


# ─── Test 4: MockProvider Gerçek SMS Göndermiyor ─────────────────────────────

@pytest.mark.asyncio
async def test_mock_provider_send_sms():
    """
    MockProvider.send_sms() gerçek HTTP çağrısı yapmadan başarılı sonuç döndürür.
    Dev ortamında gerçek Twilio credentials olmadan test yapılabilir.
    """
    provider = MockProvider()

    result = await provider.send_sms(
        to_phone="+905551234567",
        message="Test OTP: 123456",
    )

    # MockProvider başarılı yanıt döndürmeli
    assert result["status"] == "mock_sent"
    assert result["to"] == "+905551234567"


# ─── Test 5: OTP Mesaj Formatı ───────────────────────────────────────────────

def test_format_otp_message():
    """
    format_otp_message() doğru formatlı Türkçe mesaj üretmeli.
    OTP kodu mesajın içinde görünmeli.
    """
    mesaj = notification_service.format_otp_message("123456")

    assert "123456" in mesaj
    assert len(mesaj) > 10  # Anlamsız kısa mesaj değil


# ─── Test 6: Randevu İptal Mesaj Formatı ─────────────────────────────────────

def test_format_booking_cancelled_message():
    """
    format_booking_cancelled_message() slot zamanını mesaja dahil etmeli.
    """
    slot_str = "26.02.2026 14:30"
    mesaj = notification_service.format_booking_cancelled_message(slot_str)

    assert slot_str in mesaj
    assert len(mesaj) > 10


# ─── Test 7: Booking İptal — status='failed' Exception Yutulur ───────────────

@pytest.mark.asyncio
async def test_booking_cancelled_sms_basarisiz_uygulama_cokmuyor():
    """
    Booking iptal SMS'i başarısız olsa bile NotificationLog 'failed' olarak kaydedilir.
    HTTP yanıtı (randevu iptali) bu hatadan etkilenmez.
    """
    captured: dict = {}
    session = _make_mock_db_session(captured)
    db_factory = _make_mock_db_factory(session)

    mock_provider = AsyncMock(spec=SMSProvider)
    mock_provider.send_sms = AsyncMock(
        side_effect=Exception("Randevu iptali SMS gönderilemiyor")
    )

    # Exception asla dışarı çıkmamalı
    await notification_service.send_sms_task(
        db_factory=db_factory,
        provider=mock_provider,
        tenant_id=TEST_TENANT_ID,
        recipient_phone="5551234567",
        message="Randevunuz iptal edildi: 26.02.2026 14:30",
        message_type=NotificationMessageType.booking_cancelled,
    )

    # refresh() ile yakalanan gerçek NotificationLog nesnesi
    log = captured["log"]
    assert log is not None

    # Log 'failed' olarak güncellenmiş olmalı
    assert log.status == NotificationStatus.failed
    # Hata mesajı provider_response'da kayıtlı
    assert "Randevu iptali SMS gönderilemiyor" in log.provider_response["error"]
