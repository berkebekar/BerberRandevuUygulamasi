export type SuperAdminTrendPoint = {
  month: string
  count: number
}

export type SuperAdminOverviewResponse = {
  tenants: {
    total: number
    active: number
    inactive: number
    deleted: number
  }
  users: {
    total: number
  }
  bookings: {
    this_month_total: number
  }
  cancel: {
    this_month_cancelled: number
    this_month_cancel_rate: number
  }
}

export type SuperAdminTrendsResponse = {
  bookings_per_month: SuperAdminTrendPoint[]
  new_tenants_per_month: SuperAdminTrendPoint[]
  new_users_per_month: SuperAdminTrendPoint[]
}

export type SuperAdminRecentActivityItem = {
  source: string
  type: string
  title: string
  description: string | null
  tenant_id: string | null
  actor_id: string | null
  created_at: string
  meta: Record<string, unknown> | null
}

export type SuperAdminRecentActivitiesResponse = {
  items: SuperAdminRecentActivityItem[]
}

export type SuperAdminDashboardData = {
  overview: SuperAdminOverviewResponse
  trends: SuperAdminTrendsResponse
  recentActivities: SuperAdminRecentActivitiesResponse
}
