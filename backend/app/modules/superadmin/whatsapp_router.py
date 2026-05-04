"""superadmin/whatsapp_router.py — WhatsApp bot yönetim endpoint'leri."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.modules.superadmin.whatsapp_schemas import (
    WaErrorLogListResponse,
    WaHealthResponse,
    WaStatsResponse,
)
from app.modules.superadmin.whatsapp_service import (
    get_wa_health,
    get_wa_stats,
    list_wa_errors,
)

router = APIRouter(
    prefix="/superadmin/whatsapp",
    tags=["superadmin-whatsapp"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("/health", response_model=WaHealthResponse)
async def wa_health(db: AsyncSession = Depends(get_db)):
    return await get_wa_health(db)


@router.get("/stats", response_model=WaStatsResponse)
async def wa_stats(db: AsyncSession = Depends(get_db)):
    return await get_wa_stats(db)


@router.get("/errors", response_model=WaErrorLogListResponse)
async def wa_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    error_type: str | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_wa_errors(
        db,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        error_type=error_type,
        q=q,
    )
