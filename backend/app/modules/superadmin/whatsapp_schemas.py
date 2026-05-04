"""superadmin/whatsapp_schemas.py — WhatsApp bot istatistik ve hata şemaları."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.superadmin.monitoring_schemas import PaginationMeta


class WaHealthResponse(BaseModel):
    token_configured: bool
    phone_number_id_configured: bool
    errors_last_24h: int
    last_error_at: datetime | None


class WaContactStats(BaseModel):
    today: int
    this_week: int
    this_month: int


class WaBookingStats(BaseModel):
    wa_today: int
    wa_week: int
    wa_month: int
    web_today: int
    web_week: int
    web_month: int


class WaTenantBreakdown(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    wa_bookings_month: int
    web_bookings_month: int
    total_bookings_month: int


class WaStatsResponse(BaseModel):
    unique_contacts: WaContactStats
    bookings: WaBookingStats
    tenant_breakdown: list[WaTenantBreakdown]


class WaErrorLogItem(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    wa_phone: str | None
    error_type: str
    message: str
    meta_json: dict | None
    created_at: datetime


class WaErrorLogListResponse(BaseModel):
    items: list[WaErrorLogItem]
    pagination: PaginationMeta
