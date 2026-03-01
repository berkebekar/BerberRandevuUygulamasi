"""
notification/provider.py — SMS sağlayıcı soyutlama katmanı.

Bu dosya, SMS gönderimini belirli bir sağlayıcıdan bağımsız hale getirir.
Yeni sağlayıcı eklemek için SMSProvider'ı implement eden yeni bir class yeterlidir.

Mevcut sağlayıcılar:
  - TwilioProvider : Production SMS gönderimi (Twilio REST API)
  - MockProvider   : Development ortamı — gerçek SMS göndermez, console'a yazar

Gelecekte eklenebilir (MVP dışı):
  # class NetgsmProvider(SMSProvider):
  #     async def send_sms(self, to_phone: str, message: str) -> dict: ...
  #     Netgsm Türkiye'de yaygın kullanılan SMS sağlayıcısı.
  #     API dökümantasyonu: https://www.netgsm.com.tr/dokuman/
"""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ─── Provider Interface ───────────────────────────────────────────────────────

class SMSProvider(ABC):
    """
    Tüm SMS sağlayıcılarının uygulaması gereken soyut arayüz.

    Bu interface sayesinde notification/service.py hangi sağlayıcıyı
    kullandığını bilmez — sadece send_sms() çağırır.
    Değişim: get_sms_provider() factory'yi güncellemek yeterli.
    """

    @abstractmethod
    async def send_sms(self, to_phone: str, message: str) -> dict:
        """
        Belirtilen telefon numarasına SMS gönderir.

        Args:
            to_phone: Alıcı telefon numarası (E.164 formatı önerilir, örn: +905551234567)
            message: Gönderilecek mesaj metni

        Returns:
            dict: Provider'ın gönderim yanıtı (NotificationLog.provider_response olarak kaydedilir)

        Raises:
            Exception: Gönderim başarısızsa — çağıran kod bu exception'ı yakalamalıdır
        """
        ...


# ─── Twilio Provider ──────────────────────────────────────────────────────────

class TwilioProvider(SMSProvider):
    """
    Twilio REST API ile SMS gönderimi.

    Twilio, dünyada yaygın kullanılan bir SMS sağlayıcısıdır.
    API belgeleri: https://www.twilio.com/docs/sms/api
    Kimlik doğrulama: Account SID + Auth Token (Basic Auth).

    Async HTTP için httpx kullanılır — FastAPI'nin async yapısıyla uyumlu.
    """

    def __init__(self, account_sid: str, auth_token: str, from_phone: str) -> None:
        """
        Args:
            account_sid: Twilio hesap kimliği (TWILIO_ACCOUNT_SID)
            auth_token: Twilio kimlik doğrulama token'ı (TWILIO_AUTH_TOKEN)
            from_phone: Gönderen telefon numarası (TWILIO_PHONE_NUMBER)
        """
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_phone = from_phone

    async def send_sms(self, to_phone: str, message: str) -> dict:
        """
        Twilio Messages API ile SMS gönderir.

        Twilio endpoint: POST /2010-04-01/Accounts/{AccountSid}/Messages.json
        Basic Auth: account_sid:auth_token (base64 encode)

        httpx ile async gönderim — sunucu bloklanmaz.
        Başarısızlık 4xx/5xx → httpx.HTTPStatusError → exception fırlatır.
        """
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts"
            f"/{self._account_sid}/Messages.json"
        )

        async with httpx.AsyncClient() as client:
            # Twilio Basic Auth: account_sid + auth_token
            response = await client.post(
                url,
                data={
                    "To": to_phone,
                    "From": self._from_phone,
                    "Body": message,
                },
                auth=(self._account_sid, self._auth_token),
                timeout=10.0,  # 10 saniye timeout — asma kalmaması için
            )
            # 4xx veya 5xx durumunda HTTPStatusError fırlatır
            response.raise_for_status()

        logger.info("Twilio SMS sent | to=%s | sid=%s", to_phone, response.json().get("sid"))
        return response.json()


# ─── Mock Provider (Development) ─────────────────────────────────────────────

class MockProvider(SMSProvider):
    """
    Development ortamı için sahte SMS sağlayıcı.

    Gerçek SMS göndermez; mesajı logger.info ile console'a yazar.
    Bu sayede dev ortamda Twilio credentials gerekmeden test yapılabilir.
    """

    async def send_sms(self, to_phone: str, message: str) -> dict:
        """
        SMS göndermez — console'a yazar.
        Döndürdüğü dict, NotificationLog.provider_response olarak kaydedilir.
        """
        logger.info("[DEV SMS] to=%s | message=%s", to_phone, message)
        # Gerçek Twilio yanıtını taklit eden yapı
        return {"status": "mock_sent", "to": to_phone}


# ─── Provider Factory ─────────────────────────────────────────────────────────

def get_sms_provider() -> SMSProvider:
    """
    Ortama göre uygun SMS sağlayıcısını döndürür.

    Development (ENV=development):
        MockProvider — gerçek SMS göndermez, console'a yazar.
        Twilio credentials gerekmez.

    Production (ENV=production):
        TwilioProvider — gerçek SMS gönderir.
        TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER gereklidir.

    Sağlayıcı değiştirmek için:
        1. Yeni provider class'ı SMSProvider'dan türet
        2. Bu fonksiyonda return et
        Başka hiçbir dosya değişmez.
    """
    settings = get_settings()

    if settings.env != "production":
        # Dev ve test ortamlarında mock kullan — gerçek SMS gönderme
        return MockProvider()

    # Production: Twilio credentials config'den okunur
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        # Production'da credentials eksikse loglayıp mock'a dön (sessiz crash değil)
        logger.error(
            "Twilio credentials eksik (TWILIO_ACCOUNT_SID veya TWILIO_AUTH_TOKEN)."
            " MockProvider kullanılıyor — gerçek SMS GÖNDERİLMEYECEK."
        )
        return MockProvider()

    return TwilioProvider(
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        from_phone=settings.twilio_phone_number,
    )
