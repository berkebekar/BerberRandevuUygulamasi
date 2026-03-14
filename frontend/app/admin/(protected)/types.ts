import type { AdminSlotStatus } from "@/components"

export type DashboardBookingItem = {
  id: string
  user_first_name: string
  user_last_name: string
  user_phone: string
  slot_time: string
  status: "confirmed" | "cancelled" | "no_show"
  cancelled_by?: "admin" | "user" | null
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
