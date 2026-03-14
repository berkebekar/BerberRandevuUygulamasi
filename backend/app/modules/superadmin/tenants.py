"""
superadmin/tenants.py - Super admin tenant management endpoint'leri.
"""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.models.enums import TenantStatus
from app.models.super_admin import SuperAdmin
from app.modules.superadmin.tenant_schemas import (
    TenantCreateRequest,
    TenantCreateResponse,
    TenantDetailResponse,
    TenantListQuery,
    TenantListResponse,
    TenantStatusUpdateRequest,
    TenantStatusUpdateResponse,
    TenantUpdateRequest,
)
from app.modules.superadmin.tenant_service import (
    create_tenant,
    get_tenant_detail,
    list_tenants,
    soft_delete_tenant,
    update_tenant,
    update_tenant_status,
)

router = APIRouter(prefix="/superadmin/tenants", tags=["superadmin-tenants"])


@router.get("", response_model=TenantListResponse, status_code=200)
async def super_admin_list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status_filter: TenantStatus | None = Query(None, alias="status"),
    search: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort_by: Literal["created_at", "name", "subdomain", "user_count", "booking_count"] = Query("created_at"),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    _ = super_admin
    return await list_tenants(
        db,
        TenantListQuery(
            page=page,
            page_size=page_size,
            status=status_filter,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@router.get("/{tenant_id}", response_model=TenantDetailResponse, status_code=200)
async def super_admin_get_tenant_detail(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    _ = super_admin
    return await get_tenant_detail(db, tenant_id)


@router.post("", response_model=TenantCreateResponse, status_code=status.HTTP_201_CREATED)
async def super_admin_create_tenant(
    body: TenantCreateRequest,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await create_tenant(db, super_admin, body)


@router.put("/{tenant_id}", response_model=TenantDetailResponse, status_code=200)
async def super_admin_update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdateRequest,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await update_tenant(db, super_admin, tenant_id, body)


@router.put("/{tenant_id}/status", response_model=TenantStatusUpdateResponse, status_code=200)
async def super_admin_update_tenant_status(
    tenant_id: uuid.UUID,
    body: TenantStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await update_tenant_status(db, super_admin, tenant_id, body)


@router.delete("/{tenant_id}", response_model=TenantStatusUpdateResponse, status_code=200)
async def super_admin_delete_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await soft_delete_tenant(db, super_admin, tenant_id)
