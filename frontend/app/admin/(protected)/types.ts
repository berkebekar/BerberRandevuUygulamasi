import type { AdminSlotStatus } from "@/components"

export type DashboardBookingItem = {
  id: string
  user_first_name: string
  user_last_name: string
  user_phone: string
  slot_time: string
  status: "confirmed" | "cancelled" | "no_show"
  cancelled_by?: "admin" | "user" | "rescheduled_by_user" | "rescheduled_by_admin" | null
}

export type DashboardResponse = {
  date: string
  bookings: DashboardBookingItem[]
}

export type AdminOverviewResponse = {
  date: string
  is_closed: boolean
  max_booking_days_ahead: number
  bookings: DashboardBookingItem[]
  slots: { datetime: string; end_datetime?: string; status: AdminSlotStatus }[]
  blocks: { id: string; blocked_at: string; reason?: string | null }[]
}

export type ConfirmAction =
  | {
      kind: "block_slot"
      title: string
      description: string
      payload: { slotDatetime: string }
    }
  | {
      kind: "unblock_slot"
      title: string
      description: string
      payload: { blockId: string }
    }
  | {
      kind: "cancel_booking"
      title: string
      description: string
      payload: { bookingId: string }
    }
  | {
      kind: "mark_no_show"
      title: string
      description: string
      payload: { bookingId: string }
    }
  | {
      kind: "mark_confirmed"
      title: string
      description: string
      payload: { bookingId: string }
    }

export type BookingHistorySummary = {
  total_bookings: number
  completed_count: number
  upcoming_count: number
  no_show_count: number
  cancelled_count: number
}

export type BookingHistoryItem = {
  id: string
  user_first_name: string
  user_last_name: string
  user_phone: string
  slot_time: string
  status: "confirmed" | "cancelled" | "no_show"
  cancelled_by?: "admin" | "user" | "rescheduled_by_user" | "rescheduled_by_admin" | null
  created_at: string
}

export type BookingHistoryResponse = {
  start_date: string
  end_date: string
  summary: BookingHistorySummary
  items: BookingHistoryItem[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}

export type BookingHistoryStatus = "all" | "completed" | "upcoming" | "cancelled" | "no_show"
