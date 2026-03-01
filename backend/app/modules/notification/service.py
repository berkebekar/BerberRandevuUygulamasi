"""
notification/service.py — SMS gönderim iş mantığı ve NotificationLog yönetimi.

Bu dosya BackgroundTask olarak çalışan send_sms_task() fonksiyonunu içerir.
Asıl SMS gönderimi provider.py'deki sağlayıcı üzerinden yapılır.

Temel prensipler (CLAUDE.md):
  - SMS gönderimi asenkron ve non-blocking (BackgroundTask)
  - SMS başarısız olsa uygulama çökmez — tüm hatalar loglanır
  - NotificationLog'a her durumda (sent/failed) kayıt düşülür
  - Sağlayıcı değiştirilebilir — sadece get_sms_provider() güncellenir
"""

import logging
import uuid
from collections.abc import Callable

from app.models.enums import NotificationMessageType, NotificationStatus
from app.models.notification_log import NotificationLog
from app.modules.notification.provider import SMSProvider

logger = logging.getLogger(__name__)


# ─── Mesaj Formatlayıcılar ────────────────────────────────────────────────────

def format_otp_message(code: str) -> str:
    """
    OTP SMS mesajını formatlar.
    Kısa ve anlaşılır Türkçe metin — kullanıcı kodu kolayca okuyabilmeli.
    """
    return f"Randevu doğrulama kodunuz: {code}"


def format_booking_cancelled_message(slot_time_str: str) -> str:
    """
    Randevu iptali SMS mesajını formatlar.
    slot_time_str: Gösterilecek tarih-saat string'i (örn: "26 Şubat 14:30")

    Not: Bu mesaj MVP'de gönderilmez (CLAUDE.md: randevu iptali SMS MVP dışı).
    Altyapı hazır tutulur, ADIM 8 sonrasında aktif edilebilir.
    """
    return f"Randevunuz iptal edildi: {slot_time_str}"


# ─── Ana Background Task ──────────────────────────────────────────────────────

async def send_sms_task(
    db_factory: Callable,
    provider: SMSProvider,
    tenant_id: uuid.UUID,
    recipient_phone: str,
    message: str,
    message_type: NotificationMessageType,
) -> None:
    """
    SMS gönderimini background task olarak gerçekleştirir.

    Bu fonksiyon BackgroundTask olarak çalışır — HTTP yanıtı kullanıcıya
    gönderildikten SONRA başlar. Sunucu bloklanmaz.

    Akış:
    1. Yeni DB session aç (request session'ı kapanmış olabilir)
    2. NotificationLog kaydı oluştur (status='pending')
    3. provider.send_sms() ile SMS gönder
    4. Başarılı → status='sent', provider_response'u kaydet
    5. Başarısız → status='failed', hata mesajını kaydet
    6. Exception asla dışarı çıkmaz — CLAUDE.md kuralı

    db_factory parametresi neden var?
    BackgroundTask'ler FastAPI'nin request lifecycle'ı dışında çalışır.
    Request'in DB session'ı bu noktada kapanmış olabilir.
    db_factory (AsyncSessionLocal) geçilerek bağımsız yeni session açılır.

    provider parametresi neden var?
    Testlerde gerçek HTTP çağrısı yapmadan mock provider geçilebilir.
    Dependency injection prensibi — test edilebilirlik için.

    Args:
        db_factory: AsyncSessionLocal — yeni session oluşturmak için
        provider: SMS gönderim sağlayıcısı (TwilioProvider veya MockProvider)
        tenant_id: NotificationLog.tenant_id için zorunlu
        recipient_phone: Alıcı telefon numarası
        message: Gönderilecek mesaj metni
        message_type: 'otp' | 'booking_created' | 'booking_cancelled'
    """
    log = None  # Hata mesajında erişmek için dışarıda tanımlıyoruz

    try:
        # Request session'ından bağımsız yeni bir DB session aç
        async with db_factory() as db:
            try:
                # Adım 1: NotificationLog kaydı oluştur (status='pending')
                # Uygulama çökse bile bu kayıt sayesinde SMS'in denendiği bilinir
                log = NotificationLog(
                    tenant_id=tenant_id,
                    recipient_phone=recipient_phone,
                    message_type=message_type,
                    status=NotificationStatus.pending,
                )
                db.add(log)
                await db.commit()
                await db.refresh(log)

                # Adım 2: SMS gönder
                provider_response = await provider.send_sms(recipient_phone, message)

                # Adım 3: Başarılı → status='sent'
                log.status = NotificationStatus.sent
                log.provider_response = provider_response
                await db.commit()

                logger.info(
                    "SMS sent | type=%s | to=%s | log_id=%s",
                    message_type.value,
                    recipient_phone,
                    log.id,
                )

            except Exception as sms_error:
                # Adım 4: Başarısız → status='failed', hata logla, UYGULAMA ÇÖKMEZ
                logger.error(
                    "SMS send failed | type=%s | to=%s | error=%s",
                    message_type.value,
                    recipient_phone,
                    sms_error,
                )

                # NotificationLog'u 'failed' olarak güncelle
                if log is not None:
                    try:
                        log.status = NotificationStatus.failed
                        log.provider_response = {"error": str(sms_error)}
                        await db.commit()
                    except Exception as db_error:
                        # DB güncelleme de başarısız olursa sadece logla
                        logger.error(
                            "NotificationLog update failed | log_id=%s | error=%s",
                            log.id if log else "unknown",
                            db_error,
                        )

    except Exception as outer_error:
        # DB session açılamadıysa veya başka beklenmedik hata
        # Uygulama her durumda çalışmaya devam eder (CLAUDE.md)
        logger.error(
            "send_sms_task unexpected error | type=%s | to=%s | error=%s",
            message_type.value,
            recipient_phone,
            outer_error,
        )
