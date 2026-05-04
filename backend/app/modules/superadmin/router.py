"""
superadmin/router.py - Super admin auth endpoint'leri.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import resolve_cookie_domain
from app.core.database import get_db
from app.core.login_limiter import superadmin_login_limiter
from app.core.security import create_token_with_secret, decode_token_with_secret
from app.core.superadmin_auth import get_superadmin_cookie_name, get_superadmin_secret
from app.modules.superadmin.schemas import SuperAdminLoginRequest, SuperAdminLoginResponse
from app.modules.superadmin.service import (
    authenticate_super_admin,
    rotate_super_admin_session_version_by_id,
)

router = APIRouter(prefix="/superadmin/auth", tags=["superadmin-auth"])

_SESSION_MAX_AGE = 60 * 60 * 24 * 40
_SESSION_EXPIRES_MINUTES = 60 * 24 * 40


def _set_super_admin_session_cookie(
    request: Request,
    response: Response,
    super_admin_id: str,
    session_version: str,
) -> None:
    settings = get_settings()
    cookie_domain = resolve_cookie_domain(request)
    token = create_token_with_secret(
        {"sub": str(super_admin_id), "role": "superadmin", "sv": session_version},
        expires_minutes=_SESSION_EXPIRES_MINUTES,
        secret_key=get_superadmin_secret(),
    )
    response.set_cookie(
        key=settings.super_admin_cookie_name,
        value=token,
        httponly=True,
        secure=(settings.env == "production"),
        samesite="lax",
        max_age=_SESSION_MAX_AGE,
        domain=cookie_domain,
    )


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", status_code=200, response_model=SuperAdminLoginResponse)
async def super_admin_login(
    body: SuperAdminLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = _get_client_ip(request)

    blocked, retry_after = superadmin_login_limiter.check(client_ip, body.username)
    if blocked:
        raise HTTPException(
            429,
            {"error": "too_many_attempts", "retry_after": retry_after},
        )

    try:
        super_admin = await authenticate_super_admin(db, body.username, body.password)
    except HTTPException:
        superadmin_login_limiter.record_failure(client_ip, body.username)
        raise

    superadmin_login_limiter.clear(client_ip, body.username)
    _set_super_admin_session_cookie(request, response, super_admin.id, super_admin.session_version)
    return SuperAdminLoginResponse(message="login_successful")


@router.post("/logout", status_code=200)
async def super_admin_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    cookie_name = get_superadmin_cookie_name()
    token = request.cookies.get(cookie_name)

    if token:
        try:
            payload = decode_token_with_secret(token, get_superadmin_secret())
            if payload.get("role") == "superadmin" and payload.get("sub"):
                await rotate_super_admin_session_version_by_id(db, payload["sub"])
        except JWTError:
            pass

    response.delete_cookie(cookie_name, domain=resolve_cookie_domain(request))
    return {"message": "logged_out"}
