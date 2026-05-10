export type UserStatus = "active" | "blocked" | "deleted"

export type SuperAdminTenantSummary = {
  id: string
  subdomain: string
  name: string
}

export type SuperAdminUserListItem = {
  id: string
  tenant: SuperAdminTenantSummary
  phone: string
  first_name: string
  last_name: string
  status: UserStatus
  is_blocked: boolean
  created_at: string
  booking_count: number
  last_booking_at: string | null
}

export type SuperAdminUserListResponse = {
  items: SuperAdminUserListItem[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export type SuperAdminUserBookingHistoryItem = {
  id: string
  slot_time: string
  status: "confirmed" | "cancelled" | "no_show"
  cancelled_by: "admin" | "user" | null
  created_at: string
}

export type SuperAdminUserOTPItem = {
  id: string
  phone: string
  expires_at: string
  is_used: boolean
  attempt_count: number
  created_at: string
}

export type SuperAdminUserDetailResponse = {
  id: string
  tenant: SuperAdminTenantSummary
  phone: string
  first_name: string
  last_name: string
  status: UserStatus
  is_blocked: boolean
  created_at: string
  bookings: {
    items: SuperAdminUserBookingHistoryItem[]
    pagination: {
      page: number
      page_size: number
      total: number
      total_pages: number
    }
  }
  otp_requests: SuperAdminUserOTPItem[]
}

export type SuperAdminUserHardDeleteResponse = {
  id: string
  message: "user_hard_deleted"
}
