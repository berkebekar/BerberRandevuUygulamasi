"""
superadmin/tenant_schemas.py - Tenant management schema'lari.
"""

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import TenantStatus


class TenantListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
    status: TenantStatus | None = None
    search: str | None = Field(default=None, max_length=255)
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Literal["created_at", "name", "subdomain", "user_count", "booking_count"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


class TenantAdminSummary(BaseModel):
    id: uuid.UUID
    email: str
    phone: str
    created_at: datetime


class TenantListItem(BaseModel):
    id: uuid.UUID
    subdomain: str
    name: str
    status: TenantStatus
    is_active: bool
    created_at: datetime
    user_count: int
    booking_count: int


class TenantListPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class TenantListResponse(BaseModel):
    items: list[TenantListItem]
    pagination: TenantListPagination


class TenantDetailStats(BaseModel):
    user_count: int
    booking_count_total: int
    booking_count_this_month: int
    cancel_rate: float


class TenantDetailResponse(BaseModel):
    id: uuid.UUID
    subdomain: str
    name: str
    status: TenantStatus
    is_active: bool
    created_at: datetime
    admin: TenantAdminSummary | None = None
    stats: TenantDetailStats


class TenantDefaultsInput(BaseModel):
    work_start_time: time = time(9, 0)
    work_end_time: time = time(18, 0)
    slot_duration_minutes: int = Field(default=30, ge=5, le=180)
    weekly_closed_days: list[int] = Field(default_factory=lambda: [6])

    @field_validator("weekly_closed_days")
    @classmethod
    def validate_closed_days(cls, value: list[int]) -> list[int]:
        clean = sorted(set(value))
        if any(day < 0 or day > 6 for day in clean):
            raise ValueError("weekly_closed_days_invalid")
        return clean


class TenantCreateRequest(BaseModel):
    subdomain: str = Field(min_length=3, max_length=63)
    name: str = Field(min_length=2, max_length=255)
    admin_first_name: str = Field(min_length=2, max_length=255)
    admin_last_name: str = Field(min_length=2, max_length=255)
    admin_phone: str = Field(min_length=10, max_length=50)
    admin_email: str = Field(min_length=5, max_length=255)
    admin_initial_password: str = Field(min_length=8, max_length=255)
    defaults: TenantDefaultsInput | None = None


class TenantCreateResponse(BaseModel):
    tenant: TenantListItem
    admin: TenantAdminSummary


class TenantUpdateRequest(BaseModel):
    subdomain: str | None = Field(default=None, min_length=3, max_length=63)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    admin_phone: str | None = Field(default=None, min_length=10, max_length=50)
    admin_email: str | None = Field(default=None, min_length=5, max_length=255)


class TenantStatusUpdateRequest(BaseModel):
    status: Literal["active", "inactive"]
    reason: str | None = Field(default=None, max_length=500)


class TenantStatusUpdateResponse(BaseModel):
    id: uuid.UUID
    status: TenantStatus
    is_active: bool

