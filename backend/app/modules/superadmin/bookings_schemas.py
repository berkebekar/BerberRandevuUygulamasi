"""superadmin/bookings_schemas.py — Randevu listesi schema'ları."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.superadmin.monitoring_schemas import PaginationMeta


class BookingListItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_name: str
    user_id: uuid.UUID
    customer_name: str
    customer_phone: str
    slot_time: datetime
    status: str
    cancelled_by: str | None
    source: str
    created_at: datetime


class BookingListResponse(BaseModel):
    items: list[BookingListItem]
    pagination: PaginationMeta
