"""Cookie helpers shared across auth and dependency layers."""

from starlette.requests import Request

from app.core.config import get_settings


def _extract_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-host", "")
    raw_host = forwarded.split(",")[0].strip() if forwarded else request.headers.get("host", "")
    return raw_host.split(":")[0].strip().lower()


def resolve_cookie_domain(request: Request) -> str | None:
    """
    Resolve cookie domain for production and localhost-based development.

    Returns parent domain only when request host belongs to APP_DOMAIN.
    Falls back to host-only cookie when host does not match APP_DOMAIN.
    """
    settings = get_settings()
    request_host = _extract_host(request)
    if not request_host:
        return None

    app_domain = (settings.app_domain or "").strip().lower()
    if app_domain and (request_host == app_domain or request_host.endswith(f".{app_domain}")):
        return f".{app_domain}"

    if settings.env == "production":
        return None

    # Local development support: api.berber.localhost + berber.localhost -> .berber.localhost
    if request_host.endswith(".localhost"):
        labels = request_host.split(".")
        if len(labels) >= 3:
            return f".{'.'.join(labels[-2:])}"

    return None
