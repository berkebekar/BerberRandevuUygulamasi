"""
tenant_middleware.py — Her request'te Host header'dan subdomain parse edip tenant_id çözer.

Akış (CLAUDE.md TENANT MIDDLEWARE bölümü):
  1. Host header → subdomain parse et
  2. Subdomain yoksa (örn: düz "localhost") → dev modda geç, prod'da 404
  3. DB'de tenant ara (subdomain ile)
  4. Bulunamazsa → 404
  5. is_active=False ise → 403
  6. Bulunursa → request.state.tenant_id ve request.state.tenant set et

Muaf yollar: /health ve /api/v1/ dışındaki her path.
"""

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant

# Bu yollar için tenant çözümlemesi yapılmaz
_EXEMPT_PATHS = {"/health"}


def parse_subdomain(host: str) -> str | None:
    """
    Host header'dan subdomain çıkarır.

    Örnekler:
      "berber.localhost:8000" → "berber"
      "berber.app.com"        → "berber"
      "localhost:8000"        → None  (subdomain yok)
      "127.0.0.1:8000"        → None  (IP adresi, subdomain yok)
    """
    # Port numarasını temizle: "berber.localhost:8000" → "berber.localhost"
    host_clean = host.split(":")[0]
    parts = host_clean.split(".")

    # En az 2 parça olmalı ve ilk parça sayı olmamalı
    # (IP adreslerini elemek için: "127" isdigit() → True → None döner)
    if len(parts) >= 2 and not parts[0].isdigit():
        return parts[0]

    return None


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Subdomain → Tenant çözümlemesi yapar.
    Başarılı resolve'da request.state.tenant_id ve request.state.tenant set edilir.
    """

    async def dispatch(self, request: Request, call_next):
        # Muaf yollar: /health gibi endpoint'lerde tenant gerekmez
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        # Sadece /api/v1/ altındaki yollar için tenant zorunlu;
        # diğer yollar (örn: OpenAPI /docs) doğrudan geçer
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        # Next.js rewrite/proxy arkasında gerçek host bilgisi çoğunlukla
        # x-forwarded-host'ta taşınır (örn: berber.localhost:3000).
        forwarded_host = request.headers.get("x-forwarded-host", "")
        host = forwarded_host.split(",")[0].strip() if forwarded_host else request.headers.get("host", "")
        subdomain = parse_subdomain(host)

        if subdomain is None:
            # Subdomain bulunamadı (örn: düz "localhost")
            # Development modda bypass et — local test için kullanışlı
            settings = get_settings()
            if settings.env == "development":
                return await call_next(request)
            # Production'da subdomain zorunlu
            return JSONResponse({"error": "tenant_not_found"}, status_code=404)

        # DB'de subdomain'e göre tenant ara
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                # Tenant.subdomain benzersiz (UNIQUE index var), scalar_one_or_none yeterli
                select(Tenant).where(Tenant.subdomain == subdomain)
            )
            tenant = result.scalar_one_or_none()

        if tenant is None:
            # DB'de böyle bir subdomain yok → 404
            return JSONResponse({"error": "tenant_not_found"}, status_code=404)

        if not tenant.is_active:
            # Tenant pasif edilmiş → 403
            return JSONResponse({"error": "tenant_inactive"}, status_code=403)

        # Başarılı: tenant bilgisini request'e ekle
        # Bundan sonraki tüm endpoint'ler request.state.tenant_id ile tenant'ı bilir
        request.state.tenant_id = tenant.id
        request.state.tenant = tenant

        return await call_next(request)
