"""
auth/router.py — Auth HTTP endpoint'leri.

Kullanıcı (customer) endpoint'leri:
  POST /auth/user/send-otp              → OTP gönder
  POST /auth/user/verify-otp           → OTP doğrula, cookie veya registration_token döndür
  POST /auth/user/complete-registration → Yeni kullanıcı isim/soyisim ile kaydı tamamla

Admin (berber) endpoint'leri:
  POST /auth/admin/register             → Tek seferlik admin kaydı (email + telefon + şifre)
  POST /auth/admin/send-otp            → Admin telefon numarasına OTP gönder
  POST /auth/admin/verify-otp          → Admin OTP doğrula, cookie döndür
  POST /auth/admin/login/password      → Email + şifre ile giriş, cookie döndür

Ortak:
  POST /auth/logout                    → Her iki cookie'yi de temizle

Business logic auth/service.py içindedir; bu dosya sadece HTTP katmanıdır.
"""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.security import create_token
from app.models.enums import NotificationMessageType
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import (
    AdminLoginPasswordRequest,
    AdminRegisterRequest,
    AdminVerifyOTPRequest,
    CompleteRegistrationRequest,
    SendOTPRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.modules.notification import service as notification_service
from app.modules.notification.provider import get_sms_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Session cookie ömrü: 7 gün (saniye cinsinden)
_SESSION_MAX_AGE = 60 * 60 * 24 * 7
# Session token geçerlilik süresi: 7 gün (dakika cinsinden)
_SESSION_EXPIRES_MINUTES = 60 * 24 * 7


def get_tenant_id(request: Request):
    """
    TenantMiddleware tarafından request.state'e yazılan tenant_id'yi okur.
    Tenant çözümlenmemişse (test ortamında localhost bypass'ı dışında) 400 fırlatır.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(400, {"error": "tenant_required"})
    return tenant_id


def _get_provider():
    """
    Aktif SMS sağlayıcısını döndürür.
    Development: MockProvider (console'a yazar), Production: TwilioProvider.
    """
    return get_sms_provider()

def _get_cookie_domain(request: Request) -> str | None:
    """
    Cookie domain'ini belirler.

    Production:
      - Subdomain'ler arası auth için .bbsoft.com.tr gibi parent domain kullanılır.
    Dev:
      - None (domain set edilmez)
    """
    settings = get_settings()

    if settings.env != "production":
        return None

    app_domain = (settings.app_domain or "").strip().lower()
    if not app_domain:
        return None

    # Parent domain'e cookie yaz (subdomain'ler arası paylaşım için)
    return "." + app_domain

def _set_session_cookie(request: Request, response: Response, user_id) -> None:
    """
    Kullanıcı (customer) için HTTP-only session cookie set eder.
    Token içeriği: user id + role=user.
    Production'da secure=True (HTTPS zorunlu).
    """
    settings = get_settings()
    cookie_domain = _get_cookie_domain(request)
    token = create_token(
        {"sub": str(user_id), "role": "user"},
        expires_minutes=_SESSION_EXPIRES_MINUTES,
    )
    response.set_cookie(
        key="user_session",
        value=token,
        httponly=True,                          # JS erişimi yok (CLAUDE.md güvenlik kuralı)
        secure=(settings.env == "production"),  # Prod'da HTTPS zorunlu
        samesite="lax",
        max_age=_SESSION_MAX_AGE,
        domain=cookie_domain,
    )


def _set_admin_session_cookie(request: Request, response: Response, admin_id) -> None:
    """
    Admin için HTTP-only session cookie set eder.
    Cookie adı 'admin_session' — kullanıcının 'user_session' cookie'sinden ayrıdır.
    Admin cookie ile user endpoint'lerine erişim mümkün değildir (rol farkı).
    """
    settings = get_settings()
    cookie_domain = _get_cookie_domain(request)
    token = create_token(
        {"sub": str(admin_id), "role": "admin"},  # role=admin: user cookie'sinden ayrışır
        expires_minutes=_SESSION_EXPIRES_MINUTES,
    )
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,                          # JS erişimi yok (CLAUDE.md güvenlik kuralı)
        secure=(settings.env == "production"),  # Prod'da HTTPS zorunlu
        samesite="lax",
        max_age=_SESSION_MAX_AGE,
        domain=cookie_domain,
    )


@router.post("/user/send-otp", status_code=200)
async def send_otp(
    body: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Müşteri telefon numarasına 6 haneli OTP gönderir.
    OTP DB'ye yazıldıktan sonra SMS background task olarak gönderilir.
    Rate limit ihlalinde 429 döner.

    tenant_id: NotificationLog için gerekli — her log kaydına tenant bağlanır.
    """
    # Service OTP üretir ve DB'ye yazar; code SMS için döner
    code = await auth_service.send_otp(db, tenant_id, body.phone)

    # SMS background task: yanıt kullanıcıya gönderildikten sonra çalışır (non-blocking)
    # NotificationLog oluşturma + SMS gönderme + log güncelleme hepsi background'da
    background_tasks.add_task(
        notification_service.send_sms_task,
        AsyncSessionLocal,                         # background task kendi session'ını açar
        _get_provider(),                           # dev: Mock, prod: Twilio
        tenant_id,
        body.phone,
        notification_service.format_otp_message(code),
        NotificationMessageType.otp,
    )
    return {"message": "otp_sent"}


@router.post("/user/verify-otp", status_code=200, response_model=VerifyOTPResponse)
async def verify_otp(
    body: VerifyOTPRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    OTP'yi doğrular.

    Mevcut kullanıcı → HTTP-only cookie set et, {"status": "returning_user"} dön.
    Yeni kullanıcı → {"status": "new_user", "registration_token": "..."} dön (cookie YOK).
    Frontend new_user durumunda isim/soyisim formu gösterir.
    """
    result = await auth_service.verify_otp(db, tenant_id, body.phone, body.code)

    if result["status"] == "returning_user":
        user = result["user"]
        _set_session_cookie(request, response, user.id)
        return VerifyOTPResponse(status="returning_user")

    # Yeni kullanıcı: henüz kayıt tamamlanmadı, cookie set edilmez
    return VerifyOTPResponse(
        status="new_user",
        registration_token=result["registration_token"],
    )


@router.post("/user/complete-registration", status_code=200)
async def complete_registration(
    body: CompleteRegistrationRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Yeni kullanıcının kayıt sürecini tamamlar.
    verify-otp'tan alınan registration_token + isim/soyisim ile user oluşturur.
    Başarılıda HTTP-only cookie set edilir.
    """
    user = await auth_service.complete_registration(
        db, tenant_id, body.registration_token, body.first_name, body.last_name
    )
    _set_session_cookie(request, response, user.id)
    return {"status": "registered"}


# ─── Admin Endpoint'leri ──────────────────────────────────────────────────────

@router.post("/admin/register", status_code=201)
async def admin_register(
    body: AdminRegisterRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Admin (berber) tek seferlik kayıt endpoint'i.
    Bu tenant'ta zaten admin varsa 409 döner.
    Cookie set edilmez; kayıt sonrası admin login endpoint'lerini kullanmalıdır.
    """
    await auth_service.register_admin(
        db, tenant_id, body.email, body.phone, body.password
    )
    # Kayıt başarılı; sadece onay mesajı dön (bilgi sızdırmamak için id dönme)
    return {"message": "admin_registered"}


@router.post("/admin/send-otp", status_code=200)
async def admin_send_otp(
    body: SendOTPRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Admin telefon numarasına OTP gönderir.
    User OTP ile aynı mekanizma, sadece role=admin farkıyla çalışır.
    Rate limit ihlalinde 429 döner.

    tenant_id: NotificationLog için gerekli.
    """
    code = await auth_service.send_admin_otp(db, tenant_id, body.phone)
    # SMS arka planda gönderilir — kullanıcı beklemez (non-blocking)
    background_tasks.add_task(
        notification_service.send_sms_task,
        AsyncSessionLocal,
        _get_provider(),
        tenant_id,
        body.phone,
        notification_service.format_otp_message(code),
        NotificationMessageType.otp,
    )
    return {"message": "otp_sent"}


@router.post("/admin/verify-otp", status_code=200)
async def admin_verify_otp(
    body: AdminVerifyOTPRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Admin OTP'sini doğrular.
    Doğrulama başarılıysa admin_session cookie set edilir.
    Kullanıcı akışından farklı olarak "yeni kayıt" durumu yoktur —
    admin önce /auth/admin/register ile kayıt olmuş olmalıdır.
    """
    admin = await auth_service.verify_admin_otp(db, tenant_id, body.phone, body.code)
    _set_admin_session_cookie(request, response, admin.id)
    return {"message": "login_successful"}


@router.post("/admin/login/password", status_code=200)
async def admin_login_password(
    body: AdminLoginPasswordRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Email + şifre ile admin girişi.
    Başarılıysa admin_session cookie set edilir.
    Email veya şifre yanlışsa 401 döner (hangisinin yanlış olduğu belirtilmez — güvenlik).
    """
    admin = await auth_service.login_admin_password(db, tenant_id, body.email, body.password)
    _set_admin_session_cookie(request, response, admin.id)
    return {"message": "login_successful"}


# ─── Ortak: Logout ────────────────────────────────────────────────────────────

@router.post("/logout", status_code=200)
async def logout(request: Request, response: Response):
    """
    Hem user_session hem admin_session cookie'lerini temizler.
    Hangi tip kullanıcı olduğundan bağımsız çalışır; her iki cookie varsa ikisini de siler.
    """
    # Her iki cookie'yi de sil; sadece biri set edilmişse diğerini silmek sorun değil
    cookie_domain = _get_cookie_domain(request)
    response.delete_cookie("user_session", domain=cookie_domain)
    response.delete_cookie("admin_session", domain=cookie_domain)
    return {"message": "logged_out"}

