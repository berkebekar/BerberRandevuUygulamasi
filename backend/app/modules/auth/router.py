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

from fastapi import APIRouter, Depends, Request, Response
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import resolve_cookie_domain
from app.core.database import get_db
from app.core.phone import normalize_tr_phone, phone_variants
from app.core.security import create_token, decode_token
from app.models.admin import Admin
from app.models.tenant import Tenant
from app.modules.auth import service as auth_service
from app.modules.whatsapp import client as wa_client
from app.modules.auth.schemas import (
    AdminVerifyOTPRequest,
    CompleteRegistrationRequest,
    SendOTPRequest,
    UnifiedVerifyOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


async def _try_send_otp_via_whatsapp(
    db: AsyncSession,
    tenant_id,
    phone: str,
    code: str,
) -> None:
    """
    OTP kodunu WhatsApp üzerinden göndermeye çalışır.
    Tenant WA ayarları yoksa veya gönderim başarısız olursa sessizce geçer.
    OTP konsol loguna zaten yazıldığından bu fallback güvenlidir.
    """
    try:
        settings = get_settings()
        if not settings.wa_phone_number_id or not settings.wa_access_token:
            return
        try:
            normalized = normalize_tr_phone(phone)
        except Exception:
            normalized = phone
        wa_phone = normalized.lstrip("+")
        msg = (
            f"Dogrulama kodunuz: *{code}*\n\n"
            "Bu kodu web sitesindeki giris sayfasina girin.\n"
            "Kod 5 dakika gecerlidir."
        )
        await wa_client.send_text(
            settings.wa_phone_number_id,
            settings.wa_access_token,
            wa_phone,
            msg,
        )
        logger.info("[OTP-WA] WhatsApp uzerinden gonderildi | phone=%s", phone)
    except Exception as exc:
        logger.debug("WhatsApp OTP gonderilemedi (fallback: log) | error=%s", exc)

# Session cookie ömrü: 40 gün (saniye cinsinden)
_SESSION_MAX_AGE = 60 * 60 * 24 * 40
# Session token geçerlilik süresi: 40 gün (dakika cinsinden)
_SESSION_EXPIRES_MINUTES = 60 * 24 * 40


def get_tenant_id(request: Request):
    """
    TenantMiddleware tarafından request.state'e yazılan tenant_id'yi okur.
    Tenant çözümlenmemişse (test ortamında localhost bypass'ı dışında) 400 fırlatır.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(400, {"error": "tenant_required"})
    return tenant_id


def _set_session_cookie(request: Request, response: Response, user_id, session_version: str) -> None:
    """
    Kullanıcı (customer) için HTTP-only session cookie set eder.
    Token içeriği: user id + role=user.
    Production'da secure=True (HTTPS zorunlu).
    """
    settings = get_settings()
    cookie_domain = resolve_cookie_domain(request)
    token = create_token(
        {"sub": str(user_id), "role": "user", "sv": session_version},
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


def _set_admin_session_cookie(request: Request, response: Response, admin_id, session_version: str) -> None:
    """
    Admin için HTTP-only session cookie set eder.
    Cookie adı 'admin_session' — kullanıcının 'user_session' cookie'sinden ayrıdır.
    Admin cookie ile user endpoint'lerine erişim mümkün değildir (rol farkı).
    """
    settings = get_settings()
    cookie_domain = resolve_cookie_domain(request)
    token = create_token(
        {"sub": str(admin_id), "role": "admin", "sv": session_version},  # role=admin: user cookie'sinden ayrışır
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


@router.post("/send-otp", status_code=200)
async def send_otp_unified(
    body: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Tek giris endpoint'i.
    Telefon bu tenant'ta admin'e aitse admin OTP, degilse user OTP uretir.
    """
    phone_candidates = phone_variants(body.phone)
    admin_result = await db.execute(
        select(Admin).where(
            Admin.tenant_id == tenant_id,
            Admin.phone.in_(phone_candidates),
        )
    )
    admin_exists = admin_result.scalar_one_or_none() is not None

    if admin_exists:
        code = await auth_service.send_admin_otp(db, tenant_id, body.phone)
    else:
        code = await auth_service.send_otp(db, tenant_id, body.phone)
    await _try_send_otp_via_whatsapp(db, tenant_id, body.phone, code)

    logger.info("[OTP] phone=%s code=%s", body.phone, code)
    return {"message": "otp_sent"}


@router.post("/verify-otp", status_code=200, response_model=UnifiedVerifyOTPResponse)
async def verify_otp_unified(
    body: VerifyOTPRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Tek giris endpoint'i.
    Telefon admin'e aitse admin cookie, degilse user akisi calisir.
    """
    phone_candidates = phone_variants(body.phone)
    admin_result = await db.execute(
        select(Admin).where(
            Admin.tenant_id == tenant_id,
            Admin.phone.in_(phone_candidates),
        )
    )
    admin = admin_result.scalar_one_or_none()
    if admin is not None:
        verified_admin = await auth_service.verify_admin_otp(
            db,
            tenant_id,
            body.phone,
            body.code,
        )
        _set_admin_session_cookie(
            request,
            response,
            verified_admin.id,
            verified_admin.session_version,
        )
        return UnifiedVerifyOTPResponse(next="admin")

    result = await auth_service.verify_otp(db, tenant_id, body.phone, body.code)
    if result["status"] == "returning_user":
        user = result["user"]
        _set_session_cookie(request, response, user.id, user.session_version)
        return UnifiedVerifyOTPResponse(next="user")

    return UnifiedVerifyOTPResponse(
        next="register",
        registration_token=result["registration_token"],
    )


@router.post("/user/send-otp", status_code=200)
async def send_otp(
    body: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Müşteri telefon numarasına 6 haneli OTP gönderir.
    Rate limit ihlalinde 429 döner.
    """
    code = await auth_service.send_otp(db, tenant_id, body.phone)
    await _try_send_otp_via_whatsapp(db, tenant_id, body.phone, code)
    logger.info("[OTP] phone=%s code=%s", body.phone, code)
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
        _set_session_cookie(request, response, user.id, user.session_version)
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
    _set_session_cookie(request, response, user.id, user.session_version)
    return {"status": "registered"}


# ─── Admin Endpoint'leri ──────────────────────────────────────────────────────


@router.post("/admin/send-otp", status_code=200)
async def admin_send_otp(
    body: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Admin telefon numarasına OTP gönderir.
    Rate limit ihlalinde 429 döner.
    """
    code = await auth_service.send_admin_otp(db, tenant_id, body.phone)
    await _try_send_otp_via_whatsapp(db, tenant_id, body.phone, code)
    logger.info("[OTP] phone=%s code=%s", body.phone, code)
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
    _set_admin_session_cookie(request, response, admin.id, admin.session_version)
    return {"message": "login_successful"}


# ─── Ortak: Logout ────────────────────────────────────────────────────────────

@router.post("/logout", status_code=200)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    tenant_id=Depends(get_tenant_id),
):
    """
    Hem user_session hem admin_session cookie'lerini temizler.
    Hangi tip kullanıcı olduğundan bağımsız çalışır; her iki cookie varsa ikisini de siler.
    """
    # Cookie varsa ilgili token'i decode edip session_version rotate et.
    # Decode basarisizsa sadece cookie temizlenir; logout idempotent kalir.
    user_token = request.cookies.get("user_session")
    if user_token:
        try:
            payload = decode_token(user_token)
            if payload.get("role") == "user" and payload.get("sub"):
                await auth_service.rotate_user_session_version_by_id(
                    db,
                    tenant_id,
                    payload["sub"],
                )
        except JWTError:
            pass

    admin_token = request.cookies.get("admin_session")
    if admin_token:
        try:
            payload = decode_token(admin_token)
            if payload.get("role") == "admin" and payload.get("sub"):
                # Super admin impersonation token'lari gercek admin oturumunu invalid etmemeli.
                if payload.get("imp") is not True:
                    await auth_service.rotate_admin_session_version_by_id(
                        db,
                        tenant_id,
                        payload["sub"],
                    )
        except JWTError:
            pass

    # Her iki cookie'yi de sil; sadece biri set edilmişse diğerini silmek sorun değil
    cookie_domain = resolve_cookie_domain(request)
    response.delete_cookie("user_session", domain=cookie_domain)
    response.delete_cookie("admin_session", domain=cookie_domain)
    return {"message": "logged_out"}
