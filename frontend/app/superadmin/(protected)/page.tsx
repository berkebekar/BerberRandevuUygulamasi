"use client"

import dynamic from "next/dynamic"

import DashboardErrorState from "./dashboard/DashboardErrorState"
import DashboardSkeleton from "./dashboard/DashboardSkeleton"
import RecentActivityTimeline from "./dashboard/RecentActivityTimeline"
import StatsCards from "./dashboard/StatsCards"
import { useSuperAdminDashboard } from "./dashboard/useSuperAdminDashboard"

const BookingTrendChart = dynamic(() => import("./dashboard/BookingTrendChart"), {
  ssr: false,
  loading: () => <div className="h-[260px] animate-pulse rounded-xl bg-zinc-800/70" />,
})

const TenantStatusPieChart = dynamic(() => import("./dashboard/TenantStatusPieChart"), {
  ssr: false,
  loading: () => <div className="h-[260px] animate-pulse rounded-xl bg-zinc-800/70" />,
})

export default function SuperAdminDashboardPage() {
  const { data, loading, error, refetch } = useSuperAdminDashboard()

  if (loading) {
    return <DashboardSkeleton />
  }

  if (error || !data) {
    return <DashboardErrorState message={error ?? "Dashboard verisi alinamadi."} onRetry={refetch} />
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5">
        <h1 className="text-xl font-bold text-zinc-100">Super Admin Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-400">Platform istatistikleri, trendler ve son aktiviteler.</p>
      </section>

      <StatsCards overview={data.overview} />

      <section className="grid gap-4 xl:grid-cols-2">
        <BookingTrendChart points={data.trends.bookings_per_month} />
        <TenantStatusPieChart
          active={data.overview.tenants.active}
          inactive={data.overview.tenants.inactive}
          deleted={data.overview.tenants.deleted}
        />
      </section>

      <RecentActivityTimeline items={data.recentActivities.items} />
    </div>
  )
}
