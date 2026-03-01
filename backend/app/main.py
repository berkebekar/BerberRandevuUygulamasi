"""
main.py  FastAPI uygulamasinin giris noktasi.

Middleware ve tum router'lar burada kayit edilir.
Business logic yoktur; sadece baslangic noktasidir.
"""

import logging

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.core.config import get_settings
from app.middleware.tenant_middleware import TenantMiddleware
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.booking.router import router as booking_router
from app.modules.notification.router import router as notification_router
from app.modules.schedule.router import router as schedule_router
from app.modules.user.router import router as user_router

logger = logging.getLogger(__name__)


def _build_allowed_origins() -> list[str]:
    """
    CORS izinli origin listesini ayarlar.

    Kural:
    - Production: sadece kendi domain ve tenant subdomain'leri
    - Development: localhost origin'lerine izin ver
    """
    settings = get_settings()
    origins: list[str] = []

    # Development ortaminda localhost icin izin ver
    if settings.env != "production":
        origins.extend(
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ]
        )

    # Production veya dev'de ek olarak allowed_subdomains'ten izin ver
    app_domain = (settings.app_domain or "").strip()
    allowed_subdomains = [
        s.strip() for s in (settings.allowed_subdomains or "").split(",") if s.strip()
    ]

    if app_domain and allowed_subdomains:
        for sub in allowed_subdomains:
            # Yalnizca kendi domain'lerinde HTTPS izinli
            origins.append(f"https://{sub}.{app_domain}")

    return origins


def create_app() -> FastAPI:
    """
    FastAPI uygulamasini olusturur.
    Middleware ve tum modol router'larini kayit eder.
    """
    settings = get_settings()
    # Production'da debug kapali olmali
    app = FastAPI(
        title="Single Barber Appointment API",
        version="0.1.0",
        debug=(settings.env != "production"),
    )

    # TenantMiddleware: /api/v1/ altindaki her request'te subdomain  tenant gozmlemesi yapar
    # /health bu middleware'den muaftar (tenant gerekmez)
    app.add_middleware(TenantMiddleware)

    # CORS: sadece kendi domain'lerine izin ver, * yasak
    allowed_origins = _build_allowed_origins()
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,  # Cookie gonderimi icin zorunlu
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """
        HTTPException yanit formatini duzenler.
        detail bir dict ise dogrudan dondurur: {"error": "..."}
        String ise {"error": "..."} formatina sarar.
        Bu sayede tum endpoint'ler tutarli hata formati dondurur.
        """
        if isinstance(exc.detail, dict):
            return JSONResponse(exc.detail, status_code=exc.status_code)
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """
        Production ortaminda detayli hata mesajlarini kullanıciya gondermez.
        Tüm beklenmeyen hatalari loglar ve genel bir hata döner.
        """
        logger.exception("Unhandled exception", exc_info=exc)
        # Kullaniciya genel hata mesaji don
        return JSONResponse({"error": "server_error"}, status_code=500)

    @app.get("/health")
    async def health() -> dict:
        """
        Uygulamanin ayakta oldugunu dogrular.
        Docker ve load balancer health check için kullanilir.
        Tenant gerektirmez.
        """
        return {"status": "ok"}

    @app.get("/api/v1/ping")
    async def ping(request: Request) -> dict:
        """
        Middleware testleri için: request.state.tenant_id değerini dondurur.
        Tenant basarıyla gozemlendiyse tenant_id dolu gelir.
        """
        tenant_id = getattr(request.state, "tenant_id", None)
        return {"tenant_id": str(tenant_id) if tenant_id else None}

    # Tum model router'larini /api/v1/ prefix'i ile kayit et
    # su an iskelet; her adimda ilgili router dolacak
    api_prefix = "/api/v1"
    app.include_router(auth_router, prefix=api_prefix)
    app.include_router(user_router, prefix=api_prefix)
    app.include_router(admin_router, prefix=api_prefix)
    app.include_router(schedule_router, prefix=api_prefix)
    app.include_router(booking_router, prefix=api_prefix)
    app.include_router(notification_router, prefix=api_prefix)

    return app


app = create_app()
