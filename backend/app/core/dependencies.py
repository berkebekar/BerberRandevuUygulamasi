"""
dependencies.py — Tekrar kullanılabilir FastAPI dependency'leri.

Bu dosya route'ların ortak ihtiyaçlarını (kimlik doğrulama, yetkilendirme) karşılar:
  - get_tenant_id(): TenantMiddleware'den tenant_id okur; public ve korumalı endpoint'lerde kullanılır.
  - get_current_admin(): Admin gerektiren route'lar için kullanılır.
    Schedule, booking, admin panel modülleri Depends(get_current_admin) ile bu dependency'yi kullanır.
  - get_current_user(): Kullanıcı gerektiren route'lar için.
    Booking modülü Depends(get_current_user) ile bu dependency'yi kullanır.
"""

import logging

from fastapi import Cookie, Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import resolve_cookie_domain
from app.core.database import get_db
from app.core.security import create_token, decode_token
from app.models.admin import Admin
from app.models.user import User

logger = logging.getLogger(__name__)

# Sliding session süresi: 40 gün.
_SESSION_MAX_AGE = 60 * 60 * 24 * 40
_SESSION_EXPIRES_MINUTES = 60 * 24 * 40


def _renew_user_cookie(request: Request, user: User) -> None:
    """
    Her yetkili istekte user cookie'sini yeniden yazarak sliding session sağlar.
    """
    settings = get_settings()
    token = create_token(
        {"sub": str(user.id), "role": "user", "sv": user.session_version},
        expires_minutes=_SESSION_EXPIRES_MINUTES,
    )
    request.state._renew_user_session_cookie = {
        "value": token,
        "httponly": True,
        "secure": (settings.env == "production"),
        "samesite": "lax",
        "max_age": _SESSION_MAX_AGE,
        "domain": resolve_cookie_domain(request),
    }


def _renew_admin_cookie(request: Request, admin: Admin) -> None:
    """
    Her yetkili istekte admin cookie'sini yeniden yazarak sliding session sağlar.
    """
    settings = get_settings()
    token = create_token(
        {"sub": str(admin.id), "role": "admin", "sv": admin.session_version},
        expires_minutes=_SESSION_EXPIRES_MINUTES,
    )
    request.state._renew_admin_session_cookie = {
        "value": token,
        "httponly": True,
        "secure": (settings.env == "production"),
        "samesite": "lax",
        "max_age": _SESSION_MAX_AGE,
        "domain": resolve_cookie_domain(request),
    }


def get_tenant_id_from_request(request: Request):
    """
    TenantMiddleware'in request.state'e yazdığı tenant_id'yi okur.
    Bu fonksiyon get_current_admin() içinde tenant_id almak için kullanılır.
    Tenant çözümlenmemişse 400 fırlatır.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(400, {"error": "tenant_required"})
    return tenant_id


def get_tenant_id(request: Request):
    """
    Public endpoint'ler için tenant_id dependency'si.
    TenantMiddleware'den tenant_id okur; bulunamazsa 400 fırlatır.

    Kullanım:
        @router.get("/slots")
        async def get_slots(tenant_id = Depends(get_tenant_id)):
            ...
    """
    return get_tenant_id_from_request(request)


async def get_current_admin(
    request: Request,
    admin_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """
    Admin gerektiren route'lar için kimlik doğrulama dependency'si.

    Çalışma sırası:
    1. Request'ten 'admin_session' cookie'yi oku
    2. JWT'yi decode et ve role='admin' olduğunu doğrula
    3. DB'den admin'i çek (tenant_id filtreli — CLAUDE.md: her sorguda tenant_id zorunlu)
    4. Admin nesnesini döndür veya hata fırlat

    Kullanım:
        @router.get("/admin/dashboard")
        async def dashboard(admin: Admin = Depends(get_current_admin)):
            ...

    Raises:
        401: Cookie yok, JWT geçersiz veya süresi dolmuş
        403: Token var ama role='admin' değil (kullanıcı cookie'si ile erişim denemesi)
        401: DB'de admin bulunamadı (silinmiş hesap)
    """
    if admin_session is None:
        # Cookie hiç gönderilmemiş — giriş yapılmamış
        raise HTTPException(401, {"error": "not_authenticated"})

    try:
        payload = decode_token(admin_session)
    except JWTError:
        # Geçersiz imza, süresi dolmuş veya manipüle edilmiş token
        raise HTTPException(401, {"error": "invalid_token"})

    if payload.get("role") != "admin":
        # Token var ama admin cookie'si değil — user cookie ile admin route'a erişim denemesi
        raise HTTPException(403, {"error": "forbidden"})

    admin_id = payload.get("sub")
    if not admin_id:
        # Token'da sub alanı yok — hatalı token
        raise HTTPException(401, {"error": "invalid_token"})
    token_session_version = payload.get("sv")
    if not token_session_version:
        raise HTTPException(401, {"error": "invalid_token"})

    # Tenant ID'yi middleware'den al
    tenant_id = get_tenant_id_from_request(request)

    # DB'de admin'i ara — tenant_id filtresi zorunlu (CLAUDE.md)
    result = await db.execute(
        select(Admin).where(
            Admin.id == admin_id,
            Admin.tenant_id == tenant_id,  # Başka tenant'ın admin'i erişemesin
        )
    )
    admin = result.scalar_one_or_none()

    if admin is None:
        # Token geçerli ama DB'de bu admin yok (silinmiş veya tenant uyuşmazlığı)
        raise HTTPException(401, {"error": "admin_not_found"})

    # Tek aktif oturum kuralı:
    # Token'daki session_version DB'deki güncel değerle uyuşmuyorsa token iptal edilmiştir.
    if admin.session_version != token_session_version:
        raise HTTPException(401, {"error": "session_revoked"})

    # Sliding session için cookie yenilemesini response middleware'e bırak.
    _renew_admin_cookie(request, admin)

    return admin


async def get_current_user(
    request: Request,
    user_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Kullanıcı gerektiren route'lar için kimlik doğrulama dependency'si.

    Çalışma sırası:
    1. Request'ten 'user_session' cookie'yi oku
    2. JWT'yi decode et ve role='user' olduğunu doğrula
    3. DB'den kullanıcıyı çek (tenant_id filtreli — CLAUDE.md: her sorguda tenant_id zorunlu)
    4. User nesnesini döndür veya hata fırlat

    Kullanım:
        @router.post("/bookings")
        async def create_booking(user: User = Depends(get_current_user)):
            ...

    Raises:
        401: Cookie yok, JWT geçersiz veya süresi dolmuş
        403: Token var ama role='user' değil (admin cookie'si ile erişim denemesi)
        401: DB'de kullanıcı bulunamadı (silinmiş hesap)
    """
    if user_session is None:
        # Cookie hiç gönderilmemiş — giriş yapılmamış
        raise HTTPException(401, {"error": "not_authenticated"})

    try:
        payload = decode_token(user_session)
    except JWTError:
        # Geçersiz imza, süresi dolmuş veya manipüle edilmiş token
        raise HTTPException(401, {"error": "invalid_token"})

    if payload.get("role") != "user":
        # Token var ama user cookie'si değil — admin cookie ile user route'a erişim denemesi
        raise HTTPException(403, {"error": "forbidden"})

    user_id = payload.get("sub")
    if not user_id:
        # Token'da sub alanı yok — hatalı token
        raise HTTPException(401, {"error": "invalid_token"})
    token_session_version = payload.get("sv")
    if not token_session_version:
        raise HTTPException(401, {"error": "invalid_token"})

    # Tenant ID'yi middleware'den al
    tenant_id = get_tenant_id_from_request(request)

    # DB'de kullanıcıyı ara — tenant_id filtresi zorunlu (CLAUDE.md)
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,  # Başka tenant'ın kullanıcısı erişemesin
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Token geçerli ama DB'de bu kullanıcı yok (silinmiş veya tenant uyuşmazlığı)
        raise HTTPException(401, {"error": "user_not_found"})

    # Tek aktif oturum kuralı:
    # Token'daki session_version DB'deki güncel değerle uyuşmuyorsa token iptal edilmiştir.
    if user.session_version != token_session_version:
        raise HTTPException(401, {"error": "session_revoked"})

    # Sliding session için cookie yenilemesini response middleware'e bırak.
    _renew_user_cookie(request, user)

    return user
