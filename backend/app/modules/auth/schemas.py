"""
auth/schemas.py — Auth modülü Pydantic şemaları.

Request/response modellerini tanımlar; HTTP katmanı ile service katmanı arasındaki sözleşmedir.
Hem kullanıcı (customer) hem de admin akışlarının şemalarını içerir.
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator


# ─── Kullanıcı (Customer) Şemaları ───────────────────────────────────────────

class SendOTPRequest(BaseModel):
    """Telefon numarasına OTP gönderme isteği."""
    phone: str


class VerifyOTPRequest(BaseModel):
    """OTP doğrulama isteği: telefon + kullanıcının girdiği kod."""
    phone: str
    code: str


class CompleteRegistrationRequest(BaseModel):
    """
    Yeni kullanıcı kayıt tamamlama isteği.
    verify-otp'tan dönen registration_token ile isim/soyisim buraya gelir.
    """
    registration_token: str
    first_name: str
    last_name: str


class VerifyOTPResponse(BaseModel):
    """
    OTP doğrulama yanıtı.
    - returning_user: mevcut kullanıcı, cookie set edildi
    - new_user: yeni kullanıcı, registration_token döner (cookie yok)
    """
    status: Literal["returning_user", "new_user"]
    registration_token: str | None = None


class UnifiedVerifyOTPResponse(BaseModel):
    """
    Tek giris endpoint'i icin OTP dogrulama yaniti.
    - next=admin: admin_session cookie yazildi, /admin'a yonlen
    - next=user: user_session cookie yazildi, /'a yonlen
    - next=register: yeni kullanici, registration_token ile kayit adimina gec
    """

    next: Literal["admin", "user", "register"]
    registration_token: str | None = None


# ─── Admin Şemaları ───────────────────────────────────────────────────────────

class AdminRegisterRequest(BaseModel):
    """
    Admin (berber) tek seferlik kayıt isteği.
    Tenant başına yalnızca 1 admin kayıt edilebilir; ikinci denemede 409 döner.
    """
    email: EmailStr          # E-posta adresi (email+şifre girişinde kullanılır)
    phone: str               # Telefon numarası (OTP girişinde kullanılır)
    password: str            # Düz metin şifre; service katmanında bcrypt ile hash'lenir

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        """Şifre en az 8 karakter olmalıdır (CURSOR_PROMPTS ADIM 5 kuralı)."""
        if len(v) < 8:
            raise ValueError("Şifre en az 8 karakter olmalıdır")
        return v


class AdminLoginPasswordRequest(BaseModel):
    """Email + şifre ile admin giriş isteği."""
    email: EmailStr
    password: str            # Düz metin; service katmanında hash ile karşılaştırılır


class AdminVerifyOTPRequest(BaseModel):
    """
    Admin OTP doğrulama isteği.
    Önce send-otp çağrılır, ardından bu endpoint'e telefon + kod gönderilir.
    """
    phone: str
    code: str
