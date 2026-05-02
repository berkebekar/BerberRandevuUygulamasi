"""
superadmin/users.py - Super admin user management endpoint'leri.
"""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.models.enums import UserStatus
from app.models.super_admin import SuperAdmin
from app.modules.superadmin.user_schemas import (
    SuperAdminUserBlockRequest,
    SuperAdminUserDetailResponse,
    SuperAdminUserListQuery,
    SuperAdminUserListResponse,
    SuperAdminUserStatusResponse,
)
from app.modules.superadmin.user_service import (
    block_user,
    get_user_detail,
    list_users,
    restore_user,
    soft_delete_user,
    start_user_impersonation,
    unblock_user,
)

router = APIRouter(prefix="/superadmin/users", tags=["superadmin-users"])


@router.get("", response_model=SuperAdminUserListResponse, status_code=200)
async def super_admin_list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    status_filter: UserStatus | None = Query(None, alias="status"),
    search: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort_by: Literal["created_at", "phone", "first_name", "last_name", "booking_count", "last_booking_at"] = Query(
        "created_at"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc"),
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    _ = super_admin
    return await list_users(
        db,
        SuperAdminUserListQuery(
            page=page,
            page_size=page_size,
            tenant_id=tenant_id,
            status=status_filter,
            search=search,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@router.get("/{user_id}", response_model=SuperAdminUserDetailResponse, status_code=200)
async def super_admin_get_user_detail(
    user_id: uuid.UUID,
    booking_page: int = Query(1, ge=1),
    booking_page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    _ = super_admin
    return await get_user_detail(db, user_id, booking_page, booking_page_size)


@router.put("/{user_id}/block", response_model=SuperAdminUserStatusResponse, status_code=200)
async def super_admin_block_user(
    user_id: uuid.UUID,
    body: SuperAdminUserBlockRequest,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await block_user(db, super_admin, user_id, body)


@router.put("/{user_id}/unblock", response_model=SuperAdminUserStatusResponse, status_code=200)
async def super_admin_unblock_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await unblock_user(db, super_admin, user_id)


@router.put("/{user_id}/restore", response_model=SuperAdminUserStatusResponse, status_code=200)
async def super_admin_restore_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await restore_user(db, super_admin, user_id)


@router.delete("/{user_id}", response_model=SuperAdminUserStatusResponse, status_code=200)
async def super_admin_soft_delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await soft_delete_user(db, super_admin, user_id)


@router.post("/{user_id}/impersonate", status_code=status.HTTP_200_OK)
async def super_admin_start_user_impersonation(
    user_id: uuid.UUID,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    super_admin: SuperAdmin = Depends(get_current_super_admin),
):
    return await start_user_impersonation(
        db=db,
        super_admin=super_admin,
        user_id=user_id,
        request=request,
        response=response,
    )
