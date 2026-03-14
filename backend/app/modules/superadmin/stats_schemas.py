"""
superadmin/stats_schemas.py - Super admin dashboard stats response schema'lari.
"""

from datetime import datetime

from pydantic import BaseModel


class OverviewTenantStats(BaseModel):
    total: int
    active: int
    inactive: int
    deleted: int


class OverviewUserStats(BaseModel):
    total: int


class OverviewBookingStats(BaseModel):
    this_month_total: int


class OverviewCancelStats(BaseModel):
    this_month_cancelled: int
    this_month_cancel_rate: float


class SuperAdminOverviewResponse(BaseModel):
    tenants: OverviewTenantStats
    users: OverviewUserStats
    bookings: OverviewBookingStats
    cancel: OverviewCancelStats


class TrendPoint(BaseModel):
    month: str
    count: int


class SuperAdminTrendsResponse(BaseModel):
    bookings_per_month: list[TrendPoint]
    new_tenants_per_month: list[TrendPoint]
    new_users_per_month: list[TrendPoint]


class RecentActivityItem(BaseModel):
    source: str
    type: str
    title: str
    description: str | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    created_at: datetime
    meta: dict | None = None


class SuperAdminRecentActivitiesResponse(BaseModel):
    items: list[RecentActivityItem]

