export type TenantStatus = "active" | "inactive" | "deleted"

export type TenantListItem = {
  id: string
  subdomain: string
  name: string
  status: TenantStatus
  is_active: boolean
  created_at: string
  user_count: number
  booking_count: number
}

export type TenantListResponse = {
  items: TenantListItem[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export type TenantDetailResponse = {
  id: string
  subdomain: string
  name: string
  status: TenantStatus
  is_active: boolean
  created_at: string
  admin: {
    id: string
    email: string
    phone: string
    created_at: string
  } | null
  stats: {
    user_count: number
    booking_count_total: number
    booking_count_this_month: number
    cancel_rate: number
  }
}

export type TenantCreateRequest = {
  subdomain: string
  name: string
  admin_first_name: string
  admin_last_name: string
  admin_phone: string
  admin_email: string
  defaults: {
    work_start_time: string
    work_end_time: string
    slot_duration_minutes: number
    weekly_closed_days: number[]
  }
}
