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

const UserTrendChart = dynamic(() => import("./dashboard/UserTrendChart"), {
  ssr: false,
  loading: () => <div className="h-[260px] animate-pulse rounded-xl bg-zinc-800/70" />,
})

const TenantTrendChart = dynamic(() => import("./dashboard/TenantTrendChart"), {
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

      <section className="grid gap-4 xl:grid-cols-3">
        <BookingTrendChart points={data.trends.bookings_per_month} />
        <UserTrendChart points={data.trends.new_users_per_month} />
        <TenantTrendChart points={data.trends.new_tenants_per_month} />
      </section>

      <RecentActivityTimeline items={data.recentActivities.items} />
    </div>
  )
}
