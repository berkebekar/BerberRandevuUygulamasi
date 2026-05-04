"""superadmin/bookings_router.py — Tüm tenant randevuları endpoint'i."""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.modules.superadmin.bookings_schemas import BookingListResponse
from app.modules.superadmin.bookings_service import list_bookings

router = APIRouter(
    prefix="/superadmin/bookings",
    tags=["superadmin-bookings"],
    dependencies=[Depends(get_current_super_admin)],
)


@router.get("", response_model=BookingListResponse)
async def get_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    source: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_bookings(
        db,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
        status=status,
        source=source,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
