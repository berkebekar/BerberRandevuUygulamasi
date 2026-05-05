"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { SuperAdminApiError, superAdminGet } from "@/lib/superadmin-api"

type ServiceHealthItem = {
  name: string
  status: string
  response_ms: number | null
  last_checked_at: string | null
  meta: Record<string, unknown> | null
}

type MonitoringHealthResponse = {
  checked_at: string
  services: ServiceHealthItem[]
  host_resources: {
    cpu_percent: number | null
    ram_percent: number | null
    disk_percent: number | null
    ram_used_mb: number | null
    ram_total_mb: number | null
    disk_used_gb: number | null
    disk_total_gb: number | null
  } | null
}

type UptimeSummaryItem = {
  service: string
  uptime_percent: number
  checks_total: number
  checks_up: number
}

type UptimeSeriesPoint = {
  ts: string
  status: string
  response_ms: number | null
}

type UptimeSeriesItem = {
  service: string
  points: UptimeSeriesPoint[]
}

type MonitoringUptimeResponse = {
  window_hours: number
  checked_at: string
  summary: UptimeSummaryItem[]
  series: UptimeSeriesItem[]
}

type MonitoringData = {
  health: MonitoringHealthResponse
  uptime: MonitoringUptimeResponse
}

function isUpStatus(status: string): boolean {
  const normalized = status.trim().toLowerCase()
  return ["up", "ok", "operational", "healthy"].includes(normalized)
}

function getStatusClass(status: string): string {
  const normalized = status.trim().toLowerCase()
  if (["unknown", "degraded"].includes(normalized)) return "border-amber-500/40 bg-amber-500/10 text-amber-300"
  if (isUpStatus(status)) return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
  return "border-red-500/40 bg-red-500/10 text-red-300"
}

function formatDateTime(value: string | null): string {
  if (!value) return "-"
  return new Date(value).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  })
}

function parseRefreshSec(value: string | null): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return 0
  return Math.min(Math.floor(parsed), 300)
}

function formatPercent(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "-"
  return `${value.toFixed(2)}%`
}

export default function SuperAdminMonitoringPage() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [data, setData] = useState<MonitoringData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const refreshSec = parseRefreshSec(searchParams.get("refresh_sec"))
  const selectedService = searchParams.get("service") ?? "all"

  const replaceParams = useCallback(
    (updater: (next: URLSearchParams) => void) => {
      const next = new URLSearchParams(searchParams.toString())
      updater(next)
      const query = next.toString()
      router.replace(query ? `${pathname}?${query}` : pathname)
    },
    [pathname, router, searchParams]
  )

  const fetchMonitoring = useCallback(async () => {
    setError("")
    try {
      const [health, uptime] = await Promise.all([
        superAdminGet<MonitoringHealthResponse>("/api/v1/superadmin/monitoring/health"),
        superAdminGet<MonitoringUptimeResponse>("/api/v1/superadmin/monitoring/uptime"),
      ])
      setData({ health, uptime })
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Monitoring verileri yuklenemedi.")
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMonitoring()
  }, [fetchMonitoring])

  useEffect(() => {
    if (refreshSec <= 0) return
    const timer = window.setInterval(() => {
      fetchMonitoring()
    }, refreshSec * 1000)

    return () => window.clearInterval(timer)
  }, [fetchMonitoring, refreshSec])

  const serviceOptions = useMemo(() => {
    const names = data?.health.services.map((item) => item.name) ?? []
    return ["all", ...names]
  }, [data?.health.services])

  const visibleServices = useMemo(() => {
    const items = data?.health.services ?? []
    if (selectedService === "all") return items
    return items.filter((item) => item.name === selectedService)
  }, [data?.health.services, selectedService])

  const selectedUptimeSeries = useMemo(() => {
    if (!data) return []
    const serviceName = selectedService === "all" ? data.uptime.series[0]?.service : selectedService
    const item = data.uptime.series.find((entry) => entry.service === serviceName)
    return (item?.points ?? []).map((point) => ({
      ts: formatDateTime(point.ts),
      statusValue: isUpStatus(point.status) ? 1 : 0,
      responseMs: point.response_ms,
    }))
  }, [data, selectedService])

  const selectedSummary = useMemo(() => {
    if (!data) return []
    if (selectedService === "all") return data.uptime.summary
    return data.uptime.summary.filter((item) => item.service === selectedService)
  }, [data, selectedService])

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Monitoring</h1>
            <p className="mt-1 text-sm text-zinc-400">Sistem saglik durumu, uptime ve response metrikleri.</p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedService}
              onChange={(event) =>
                replaceParams((next) => {
                  if (event.target.value === "all") next.delete("service")
                  else next.set("service", event.target.value)
                })
              }
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              {serviceOptions.map((service) => (
                <option key={service} value={service}>
                  {service === "all" ? "Tum servisler" : service}
                </option>
              ))}
            </select>

            <select
              value={String(refreshSec)}
              onChange={(event) =>
                replaceParams((next) => {
                  const value = Number(event.target.value)
                  if (value <= 0) next.delete("refresh_sec")
                  else next.set("refresh_sec", String(value))
                })
              }
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="0">Auto refresh: Kapali</option>
              <option value="15">15 sn</option>
              <option value="30">30 sn</option>
              <option value="60">60 sn</option>
            </select>

            <button
              type="button"
              onClick={() => fetchMonitoring()}
              className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-100"
            >
              Yenile
            </button>
          </div>
        </div>
      </section>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}

      {loading ? (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <div className="h-32 animate-pulse rounded-xl bg-zinc-800/70" />
          <div className="h-32 animate-pulse rounded-xl bg-zinc-800/70" />
          <div className="h-32 animate-pulse rounded-xl bg-zinc-800/70" />
        </section>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {visibleServices.map((service) => (
              <article key={service.name} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-zinc-100">{service.name}</h2>
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${getStatusClass(service.status)}`}>
                    {service.status}
                  </span>
                </div>
                <p className="mt-3 text-2xl font-bold text-zinc-100">
                  {service.response_ms != null ? `${service.response_ms.toFixed(2)} ms` : "-"}
                </p>
                <p className="mt-1 text-xs text-zinc-400">Last check: {formatDateTime(service.last_checked_at)}</p>
              </article>
            ))}
          </section>

          <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
            <h2 className="text-sm font-semibold text-zinc-100">VPS Kaynak Kullanimi</h2>
            <p className="mt-1 text-xs text-zinc-400">CPU, RAM ve Disk kullanim oranlari (canli olcum).</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <article className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                <p className="text-xs text-zinc-400">CPU</p>
                <p className="mt-1 text-xl font-bold text-zinc-100">
                  {formatPercent(data?.health.host_resources?.cpu_percent ?? null)}
                </p>
              </article>
              <article className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                <p className="text-xs text-zinc-400">RAM</p>
                <p className="mt-1 text-xl font-bold text-zinc-100">
                  {formatPercent(data?.health.host_resources?.ram_percent ?? null)}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {data?.health.host_resources?.ram_used_mb != null &&
                  data?.health.host_resources?.ram_total_mb != null
                    ? `${data.health.host_resources.ram_used_mb.toFixed(0)} / ${data.health.host_resources.ram_total_mb.toFixed(0)} MB`
                    : "-"}
                </p>
              </article>
              <article className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                <p className="text-xs text-zinc-400">Disk</p>
                <p className="mt-1 text-xl font-bold text-zinc-100">
                  {formatPercent(data?.health.host_resources?.disk_percent ?? null)}
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  {data?.health.host_resources?.disk_used_gb != null &&
                  data?.health.host_resources?.disk_total_gb != null
                    ? `${data.health.host_resources.disk_used_gb.toFixed(2)} / ${data.health.host_resources.disk_total_gb.toFixed(2)} GB`
                    : "-"}
                </p>
              </article>
            </div>
          </section>

          <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
            <h2 className="text-sm font-semibold text-zinc-100">Uptime ({data?.uptime.window_hours ?? 24} saat)</h2>
            <p className="mt-1 text-xs text-zinc-400">Secili servis icin durum serisi (1=up, 0=down)</p>

            {selectedUptimeSeries.length === 0 ? (
              <div className="mt-3 rounded-lg border border-dashed border-zinc-700 px-4 py-8 text-center text-sm text-zinc-500">
                Uptime verisi bulunamadi.
              </div>
            ) : (
              <div className="mt-3 h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={selectedUptimeSeries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#3f3f46" />
                    <XAxis dataKey="ts" stroke="#a1a1aa" minTickGap={40} />
                    <YAxis stroke="#a1a1aa" domain={[0, 1]} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#18181b", borderColor: "#3f3f46", borderRadius: 8 }}
                      labelStyle={{ color: "#e4e4e7" }}
                    />
                    <Line type="stepAfter" dataKey="statusValue" stroke="#22c55e" strokeWidth={2.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {selectedSummary.map((item) => (
              <article key={item.service} className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
                <h3 className="text-sm font-semibold text-zinc-100">{item.service}</h3>
                <p className="mt-2 text-2xl font-bold text-zinc-100">{item.uptime_percent.toFixed(2)}%</p>
                <p className="mt-1 text-xs text-zinc-400">
                  {item.checks_up} / {item.checks_total} kontrol basarili
                </p>
              </article>
            ))}
          </section>
        </>
      )}
    </div>
  )
}
