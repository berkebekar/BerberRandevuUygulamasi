"""
superadmin/impersonation.py - Super admin tenant impersonation endpoint'leri.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import resolve_cookie_domain
from app.core.database import get_db
from app.core.security import create_token, decode_token
from app.models.activity_log import ActivityLog
from app.models.admin import Admin
from app.models.enums import TenantStatus
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.core.dependencies import get_current_super_admin

router = APIRouter(prefix="/superadmin", tags=["superadmin-impersonation"])

_IMPERSONATION_TTL_SECONDS = 60 * 60
_IMPERSONATION_EXPIRES_MINUTES = 60


def _set_admin_impersonation_cookie(
    request: Request,
    response: Response,
    admin: Admin,
    super_admin: SuperAdmin,
    tenant: Tenant,
) -> int:
    now_epoch = int(datetime.now(timezone.utc).timestamp())
    imp_exp_epoch = now_epoch + _IMPERSONATION_TTL_SECONDS
    token = create_token(
        {
            "sub": str(admin.id),
            "role": "admin",
            "sv": admin.session_version,
            "imp": True,
            "imp_by": str(super_admin.id),
            "imp_tenant": str(tenant.id),
            "imp_exp": imp_exp_epoch,
        },
        expires_minutes=_IMPERSONATION_EXPIRES_MINUTES,
    )
    settings = get_settings()
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        secure=(settings.env == "production"),
        samesite="lax",
        max_age=_IMPERSONATION_TTL_SECONDS,
        domain=resolve_cookie_domain(request),
    )
    return _IMPERSONATION_TTL_SECONDS


async def _log_activity(
    db: AsyncSession,
    super_admin: SuperAdmin,
    action_type: str,
    tenant_id: uuid.UUID | None,
    entity_id: str | None = None,
    metadata_json: dict | None = None,
) -> None:
    db.add(
        ActivityLog(
            super_admin_id=super_admin.id,
            action_type=action_type,
            entity_type="impersonation",
            entity_id=entity_id,
            tenant_id=tenant_id,
            metadata_json=metadata_json,
        )
    )


@router.post("/tenants/{tenant_id}/impersonate", status_code=200)
async def start_tenant_admin_impersonation(
    tenant_id: uuid.UUID,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(404, {"error": "tenant_not_found"})
    if tenant.status == TenantStatus.deleted:
        raise HTTPException(409, {"error": "tenant_deleted"})

    admin_result = await db.execute(select(Admin).where(Admin.tenant_id == tenant.id))
    admin = admin_result.scalar_one_or_none()
    if admin is None:
        raise HTTPException(404, {"error": "admin_not_found"})

    expires_in_seconds = _set_admin_impersonation_cookie(
        request=request,
        response=response,
        admin=admin,
        super_admin=super_admin,
        tenant=tenant,
    )
    await _log_activity(
        db=db,
        super_admin=super_admin,
        action_type="impersonation_started",
        tenant_id=tenant.id,
        entity_id=str(admin.id),
        metadata_json={"ttl_seconds": expires_in_seconds},
    )
    await db.commit()
    return {"message": "impersonation_started", "expires_in_seconds": expires_in_seconds}


@router.post("/impersonate/exit", status_code=200)
async def exit_tenant_admin_impersonation(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    tenant_id: uuid.UUID | None = None
    admin_id: str | None = None
    token = request.cookies.get("admin_session")
    if token:
        try:
            payload = decode_token(token)
            if payload.get("imp") is True:
                admin_id = str(payload.get("sub")) if payload.get("sub") else None
                raw_tenant_id = payload.get("imp_tenant")
                if raw_tenant_id:
                    tenant_id = uuid.UUID(str(raw_tenant_id))
        except (JWTError, ValueError, TypeError):
            pass

    response.delete_cookie("admin_session", domain=resolve_cookie_domain(request))
    await _log_activity(
        db=db,
        super_admin=super_admin,
        action_type="impersonation_ended",
        tenant_id=tenant_id,
        entity_id=admin_id,
    )
    await db.commit()
    return {"message": "impersonation_ended"}

