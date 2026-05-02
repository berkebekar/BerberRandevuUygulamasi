"use client"

import { useCallback, useEffect, useState } from "react"

import { SuperAdminApiError, superAdminGet } from "@/lib/superadmin-api"

import type {
  SuperAdminDashboardData,
  SuperAdminOverviewResponse,
  SuperAdminRecentActivitiesResponse,
  SuperAdminTrendsResponse,
} from "./types"

type UseSuperAdminDashboardResult = {
  data: SuperAdminDashboardData | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export function useSuperAdminDashboard(): UseSuperAdminDashboardResult {
  const [data, setData] = useState<SuperAdminDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboardData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [overview, trends, recentActivities] = await Promise.all([
        superAdminGet<SuperAdminOverviewResponse>("/api/v1/superadmin/stats/overview"),
        superAdminGet<SuperAdminTrendsResponse>("/api/v1/superadmin/stats/trends"),
        superAdminGet<SuperAdminRecentActivitiesResponse>("/api/v1/superadmin/stats/recent-activities?limit=10"),
      ])

      setData({
        overview,
        trends,
        recentActivities,
      })
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) {
        setError(err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Dashboard verileri su an yuklenemiyor.")
      }
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDashboardData()
  }, [fetchDashboardData])

  return {
    data,
    loading,
    error,
    refetch: fetchDashboardData,
  }
}
