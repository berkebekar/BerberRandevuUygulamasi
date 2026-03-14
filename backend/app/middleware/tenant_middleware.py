"""
tenant_middleware.py - Resolve tenant from host/subdomain for /api/v1 routes.

Rules:
- /health is exempt.
- /api/v1/superadmin/* is exempt from tenant resolution.
- In development, missing subdomain is allowed.
- In production, missing subdomain returns tenant_not_found.
"""

from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.enums import TenantStatus
from app.models.tenant import Tenant

_EXEMPT_PATHS = {"/health"}


def parse_subdomain(host: str) -> str | None:
    """
    Extract subdomain from Host header.

    Examples:
    - berber.localhost:8000 -> berber
    - berber.app.com -> berber
    - localhost:8000 -> None
    - 127.0.0.1:8000 -> None
    """
    host_clean = host.split(":")[0]
    parts = host_clean.split(".")

    if len(parts) >= 2 and not parts[0].isdigit():
        return parts[0]
    return None


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve tenant and write it into request.state."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        if request.url.path.startswith("/api/v1/superadmin/"):
            return await call_next(request)

        forwarded_host = request.headers.get("x-forwarded-host", "")
        host = forwarded_host.split(",")[0].strip() if forwarded_host else request.headers.get("host", "")
        subdomain = parse_subdomain(host)

        if subdomain is None:
            settings = get_settings()
            if settings.env == "development":
                return await call_next(request)
            return JSONResponse({"error": "tenant_not_found"}, status_code=404)

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Tenant).where(Tenant.subdomain == subdomain))
            tenant = result.scalar_one_or_none()

        if tenant is None:
            return JSONResponse({"error": "tenant_not_found"}, status_code=404)

        # Source of truth: tenant.status
        tenant_status = getattr(tenant, "status", None)
        if tenant_status == TenantStatus.deleted:
            return JSONResponse({"error": "tenant_deleted"}, status_code=404)
        if tenant_status == TenantStatus.inactive:
            return JSONResponse({"error": "tenant_inactive"}, status_code=403)

        # Compatibility fallback for older rows without status.
        if tenant_status is None and not tenant.is_active:
            return JSONResponse({"error": "tenant_inactive"}, status_code=403)

        request.state.tenant_id = tenant.id
        request.state.tenant = tenant
        return await call_next(request)
