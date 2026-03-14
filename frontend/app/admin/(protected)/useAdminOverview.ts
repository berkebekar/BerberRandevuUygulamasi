"use client"

import { useCallback, useEffect, useState } from "react"
import type { AdminSlotItem } from "@/components"
import { apiFetch } from "@/lib/api"
import type { AdminOverviewResponse, DashboardResponse } from "./types"
import { mapAdminError, normalizeKey } from "./utils"

type UseAdminOverviewResult = {
  maxBookingDaysAhead: number
  dashboard: DashboardResponse | null
  dashboardLoading: boolean
  slots: AdminSlotItem[]
  slotLoading: boolean
  blockMap: Record<string, string>
  fetchOverview: (date: string, options?: { silent?: boolean }) => Promise<void>
}

export function useAdminOverview(
  selectedDate: string,
  onError: (message: string) => void
): UseAdminOverviewResult {
  const [maxBookingDaysAhead, setMaxBookingDaysAhead] = useState(14)
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [slots, setSlots] = useState<AdminSlotItem[]>([])
  const [slotLoading, setSlotLoading] = useState(false)
  const [blockMap, setBlockMap] = useState<Record<string, string>>({})

  const fetchOverview = useCallback(
    async (date: string, options?: { silent?: boolean }) => {
      const silent = options?.silent ?? false
      if (!silent) {
        setDashboardLoading(true)
        setSlotLoading(true)
      }

      try {
        const data = await apiFetch<AdminOverviewResponse>(`/api/v1/admin/overview?date=${date}`)
        setMaxBookingDaysAhead(data.max_booking_days_ahead ?? 14)
        setDashboard({
          date: data.date,
          bookings: data.bookings,
        })
        setSlots(
          (data.slots ?? []).map((slot) => ({
            datetime: slot.datetime,
            end_datetime: slot.end_datetime,
            status: slot.status,
          }))
        )

        const nextMap: Record<string, string> = {}
        for (const block of data.blocks ?? []) {
          nextMap[normalizeKey(block.blocked_at)] = block.id
        }
        setBlockMap(nextMap)
      } catch (err: unknown) {
        setDashboard(null)
        setSlots([])
        setBlockMap({})
        onError(mapAdminError(err))
      } finally {
        if (!silent) {
          setDashboardLoading(false)
          setSlotLoading(false)
        }
      }
    },
    [onError]
  )

  useEffect(() => {
    fetchOverview(selectedDate)
  }, [selectedDate, fetchOverview])

  useEffect(() => {
    const refreshOverview = () => {
      if (document.hidden) return
      fetchOverview(selectedDate, { silent: true })
    }

    const intervalId = window.setInterval(refreshOverview, 15000)
    const onVisibilityChange = () => {
      if (!document.hidden) fetchOverview(selectedDate, { silent: true })
    }

    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => {
      window.clearInterval(intervalId)
      document.removeEventListener("visibilitychange", onVisibilityChange)
    }
  }, [selectedDate, fetchOverview])

  return {
    maxBookingDaysAhead,
    dashboard,
    dashboardLoading,
    slots,
    slotLoading,
    blockMap,
    fetchOverview,
  }
}
