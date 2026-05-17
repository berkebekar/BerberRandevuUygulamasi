"""
superadmin/tenant_schemas.py - Tenant management schema'lari.
"""

import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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


class TenantParentSummary(BaseModel):
    id: uuid.UUID
    subdomain: str
    name: str
    first_name: str | None = None
    last_name: str | None = None


class TenantListItem(BaseModel):
    id: uuid.UUID
    parent_tenant_id: uuid.UUID | None = None
    subdomain: str
    name: str
    address: str | None = None
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


class TenantWhatsappSettings(BaseModel):
    phone_number_id: str | None = None
    waba_id: str | None = None
    display_phone_number: str | None = None
    connection_status: Literal["disconnected", "connected", "pending", "error"] = "disconnected"
    connected_at: datetime | None = None
    bot_enabled: bool = True
    bot_superadmin_enabled: bool = True
    bot_effective_enabled: bool = True
    booking_enabled: bool = True
    booking_superadmin_enabled: bool = True
    booking_effective_enabled: bool = True
    reminder_enabled: bool = True
    reminder_superadmin_enabled: bool = True
    reminder_effective_enabled: bool = True
    cancellation_enabled: bool = True
    cancellation_superadmin_enabled: bool = True
    cancellation_effective_enabled: bool = True
    reschedule_enabled: bool = True
    reschedule_superadmin_enabled: bool = True
    reschedule_effective_enabled: bool = True
    silent_numbers: list[str] = Field(default_factory=list)


class TenantDetailResponse(BaseModel):
    id: uuid.UUID
    parent_tenant_id: uuid.UUID | None = None
    subdomain: str
    name: str
    address: str | None = None
    status: TenantStatus
    is_active: bool
    created_at: datetime
    admin: TenantAdminSummary | None = None
    parent_tenant: TenantParentSummary | None = None
    whatsapp: TenantWhatsappSettings
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
    parent_tenant_id: uuid.UUID | None = None
    subdomain: str = Field(min_length=3, max_length=63)
    name: str = Field(min_length=2, max_length=255)
    address: str = Field(min_length=5, max_length=500)
    admin_first_name: str = Field(min_length=2, max_length=255)
    admin_last_name: str = Field(min_length=2, max_length=255)
    admin_phone: str = Field(min_length=10, max_length=50)
    admin_email: str = Field(min_length=5, max_length=255)
    defaults: TenantDefaultsInput | None = None


class TenantDomainSyncResponse(BaseModel):
    enabled: bool
    updated: bool = False
    deploy_requested: bool = False
    deployment_uuid: str | None = None
    reason: str | None = None
    domain: str | None = None
    domains: list[str] = Field(default_factory=list)
    tenant_count: int = 0
    error: str | None = None


class TenantCreateResponse(BaseModel):
    tenant: TenantListItem
    admin: TenantAdminSummary
    domain_sync: TenantDomainSyncResponse | None = None


class TenantUpdateRequest(BaseModel):
    parent_tenant_id: uuid.UUID | None = None
    subdomain: str | None = Field(default=None, min_length=3, max_length=63)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    address: str | None = Field(default=None, min_length=5, max_length=500)
    admin_phone: str | None = Field(default=None, min_length=10, max_length=50)
    admin_email: str | None = Field(default=None, min_length=5, max_length=255)


class TenantWhatsappUpdateRequest(BaseModel):
    phone_number_id: str | None = Field(default=None, max_length=100)
    waba_id: str | None = Field(default=None, max_length=100)
    display_phone_number: str | None = Field(default=None, max_length=50)
    connection_status: Literal["disconnected", "connected", "pending", "error"] = "disconnected"
    bot_enabled: bool = True
    bot_superadmin_enabled: bool = True
    booking_enabled: bool = True
    booking_superadmin_enabled: bool = True
    reminder_enabled: bool = True
    reminder_superadmin_enabled: bool = True
    cancellation_enabled: bool = True
    cancellation_superadmin_enabled: bool = True
    reschedule_enabled: bool = True
    reschedule_superadmin_enabled: bool = True
    silent_numbers: list[str] = Field(default_factory=list)

    @field_validator("phone_number_id", "waba_id", "display_phone_number")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_connected_state(self) -> "TenantWhatsappUpdateRequest":
        if self.connection_status == "connected" and not self.phone_number_id:
            raise ValueError("connected_whatsapp_requires_phone_number_id")
        return self


class TenantStatusUpdateRequest(BaseModel):
    status: Literal["active", "inactive"]
    reason: str | None = Field(default=None, max_length=500)


class TenantStatusUpdateResponse(BaseModel):
    id: uuid.UUID
    status: TenantStatus
    is_active: bool


class TenantParentCandidate(BaseModel):
    id: uuid.UUID
    subdomain: str
    name: str
    first_name: str | None = None
    last_name: str | None = None


class TenantParentCandidatesResponse(BaseModel):
    items: list[TenantParentCandidate]


class TenantHardDeleteResponse(BaseModel):
    id: uuid.UUID
    message: Literal["tenant_hard_deleted"]
