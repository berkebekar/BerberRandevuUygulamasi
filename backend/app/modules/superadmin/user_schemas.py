"""
superadmin/user_schemas.py - Super admin user management schema'lari.
"""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import BookingStatus, CancelledBy, UserStatus


class SuperAdminUserListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=100)
    tenant_id: uuid.UUID | None = None
    status: UserStatus | None = None
    search: str | None = Field(default=None, max_length=255)
    date_from: date | None = None
    date_to: date | None = None
    sort_by: Literal["created_at", "phone", "first_name", "last_name", "booking_count", "last_booking_at"] = (
        "created_at"
    )
    sort_order: Literal["asc", "desc"] = "desc"


class SuperAdminTenantSummary(BaseModel):
    id: uuid.UUID
    subdomain: str
    name: str


class SuperAdminUserListItem(BaseModel):
    id: uuid.UUID
    tenant: SuperAdminTenantSummary
    phone: str
    first_name: str
    last_name: str
    status: UserStatus
    is_blocked: bool
    created_at: datetime
    booking_count: int
    last_booking_at: datetime | None = None


class SuperAdminUserListPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class SuperAdminUserListResponse(BaseModel):
    items: list[SuperAdminUserListItem]
    pagination: SuperAdminUserListPagination


class SuperAdminUserBookingHistoryItem(BaseModel):
    id: uuid.UUID
    slot_time: datetime
    status: BookingStatus
    cancelled_by: CancelledBy | None = None
    created_at: datetime


class SuperAdminUserBookingHistoryPagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class SuperAdminUserBookingHistory(BaseModel):
    items: list[SuperAdminUserBookingHistoryItem]
    pagination: SuperAdminUserBookingHistoryPagination


class SuperAdminUserOTPItem(BaseModel):
    id: uuid.UUID
    phone: str
    expires_at: datetime
    is_used: bool
    attempt_count: int
    created_at: datetime


class SuperAdminUserDetailResponse(BaseModel):
    id: uuid.UUID
    tenant: SuperAdminTenantSummary
    phone: str
    first_name: str
    last_name: str
    status: UserStatus
    is_blocked: bool
    created_at: datetime
    bookings: SuperAdminUserBookingHistory
    otp_requests: list[SuperAdminUserOTPItem]


class SuperAdminUserBlockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SuperAdminUserStatusResponse(BaseModel):
    id: uuid.UUID
    status: UserStatus
    is_blocked: bool


class SuperAdminUserHardDeleteResponse(BaseModel):
    id: uuid.UUID
    message: Literal["user_hard_deleted"]
