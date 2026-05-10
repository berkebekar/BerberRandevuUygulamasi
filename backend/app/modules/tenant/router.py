"""tenant/router.py - Tenant bilgisi endpoint'leri."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.models.tenant import Tenant
from app.models.admin import Admin

router = APIRouter(prefix="/tenant", tags=["tenant"])


class TenantInfoResponse(BaseModel):
    name: str
    phone: str | None = None
    address: str | None = None


@router.get("/info", response_model=TenantInfoResponse)
async def get_tenant_info(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Tenant'ın görünen adını döndürür. Auth gerektirmez."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(404, {"error": "tenant_not_found"})

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(404, {"error": "tenant_not_found"})

    fn = (tenant.first_name or "").strip()
    ln = (tenant.last_name or "").strip()
    if fn and ln:
        display_name = f"{fn} {ln}"
    elif fn or ln:
        display_name = fn or ln
    else:
        display_name = tenant.name

    admin_result = await db.execute(select(Admin).where(Admin.tenant_id == tenant.id))
    admin = admin_result.scalar_one_or_none()

    return TenantInfoResponse(
        name=display_name,
        phone=admin.phone if admin else None,
        address=tenant.address,
    )
