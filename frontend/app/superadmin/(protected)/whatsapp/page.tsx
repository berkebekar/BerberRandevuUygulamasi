"use client"

import { useCallback, useEffect, useState } from "react"
import { SuperAdminApiError, superAdminGet } from "@/lib/superadmin-api"

// ─── Tipler ──────────────────────────────────────────────────────────────────

type WaHealth = {
  token_configured: boolean
  phone_number_id_configured: boolean
  errors_last_24h: number
  last_error_at: string | null
}

type WaContactStats = { today: number; this_week: number; this_month: number }
type WaBookingStats = {
  wa_today: number; wa_week: number; wa_month: number
  web_today: number; web_week: number; web_month: number
}
type WaTenantBreakdown = {
  tenant_id: string
  tenant_name: string
  wa_bookings_month: number
  web_bookings_month: number
  total_bookings_month: number
}
type WaStats = {
  unique_contacts: WaContactStats
  bookings: WaBookingStats
  tenant_breakdown: WaTenantBreakdown[]
}

type WaErrorItem = {
  id: string
  tenant_id: string | null
  wa_phone: string | null
  error_type: string
  message: string
  meta_json: Record<string, unknown> | null
  created_at: string
}
type WaErrorList = {
  items: WaErrorItem[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

// ─── Yardımcılar ─────────────────────────────────────────────────────────────

function fmt(dt: string | null) {
  if (!dt) return "—"
  return new Date(dt).toLocaleString("tr-TR", {
    dateStyle: "short", timeStyle: "short", timeZone: "Europe/Istanbul",
  })
}

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
      ok
        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
        : "border-red-500/40 bg-red-500/10 text-red-300"
    }`}>
      <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-400" : "bg-red-400"}`} />
      {label}
    </span>
  )
}

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
      <p className="text-xs text-zinc-400">{label}</p>
      <p className="mt-1.5 text-2xl font-bold text-zinc-100">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-zinc-500">{sub}</p>}
    </div>
  )
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function SuperAdminWhatsAppPage() {
  const [health, setHealth] = useState<WaHealth | null>(null)
  const [stats, setStats] = useState<WaStats | null>(null)
  const [errors, setErrors] = useState<WaErrorList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // hata logu filtreleri
  const [errPage, setErrPage] = useState(1)
  const [errType, setErrType] = useState("")
  const [errQ, setErrQ] = useState("")
  const [errSearchInput, setErrSearchInput] = useState("")

  const fetchAll = useCallback(async () => {
    setError("")
    try {
      const [h, s] = await Promise.all([
        superAdminGet<WaHealth>("/api/v1/superadmin/whatsapp/health"),
        superAdminGet<WaStats>("/api/v1/superadmin/whatsapp/stats"),
      ])
      setHealth(h)
      setStats(s)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Veriler yuklenemedi.")
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchErrors = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(errPage), page_size: "50" })
      if (errType) params.set("error_type", errType)
      if (errQ) params.set("q", errQ)
      const data = await superAdminGet<WaErrorList>(`/api/v1/superadmin/whatsapp/errors?${params}`)
      setErrors(data)
    } catch {
      // hata tablosu yüklenemese ana hata gösterilmez
    }
  }, [errPage, errType, errQ])

  useEffect(() => { fetchAll() }, [fetchAll])
  useEffect(() => { fetchErrors() }, [fetchErrors])

  const ERROR_TYPES = ["config_error", "user_create_failed", "booking_failed", "webhook_error", "send_failed"]

  return (
    <div className="space-y-5">

      {/* Başlık */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">WhatsApp Bot</h1>
            <p className="mt-1 text-sm text-zinc-400">Bot sağlık durumu, temas istatistikleri ve hata kayıtları.</p>
          </div>
          <button
            onClick={() => { setLoading(true); fetchAll(); fetchErrors() }}
            className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-100 hover:bg-zinc-800/50"
          >
            Yenile
          </button>
        </div>
      </section>

      {error && (
        <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>
      )}

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-zinc-800/70" />
          ))}
        </div>
      ) : (
        <>
          {/* ── Bot Sağlığı ─────────────────────────────────────────────── */}
          <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
            <h2 className="mb-3 text-sm font-semibold text-zinc-200">Bot Sağlığı</h2>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge ok={!!health?.token_configured} label="Access Token" />
              <StatusBadge ok={!!health?.phone_number_id_configured} label="Phone Number ID" />
              <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                (health?.errors_last_24h ?? 0) === 0
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-300"
              }`}>
                Son 24s hata: {health?.errors_last_24h ?? 0}
              </span>
              {health?.last_error_at && (
                <span className="text-xs text-zinc-500">Son hata: {fmt(health.last_error_at)}</span>
              )}
            </div>
          </section>

          {/* ── Benzersiz Temas İstatistikleri ─────────────────────────── */}
          <section>
            <h2 className="mb-3 text-sm font-semibold text-zinc-400 uppercase tracking-wider">Benzersiz Temas (Farklı Numara)</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label="Bugün" value={stats?.unique_contacts.today ?? 0} />
              <StatCard label="Bu Hafta" value={stats?.unique_contacts.this_week ?? 0} />
              <StatCard label="Bu Ay" value={stats?.unique_contacts.this_month ?? 0} />
            </div>
          </section>

          {/* ── Randevu Kaynak Dağılımı ─────────────────────────────────── */}
          <section>
            <h2 className="mb-3 text-sm font-semibold text-zinc-400 uppercase tracking-wider">Randevu Kaynağı</h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-2">
                <p className="text-xs font-medium text-emerald-400">WhatsApp üzerinden</p>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Bugün</span>
                  <span className="font-semibold text-zinc-100">{stats?.bookings.wa_today ?? 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Bu hafta</span>
                  <span className="font-semibold text-zinc-100">{stats?.bookings.wa_week ?? 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Bu ay</span>
                  <span className="font-semibold text-zinc-100">{stats?.bookings.wa_month ?? 0}</span>
                </div>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 space-y-2">
                <p className="text-xs font-medium text-blue-400">Web üzerinden</p>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Bugün</span>
                  <span className="font-semibold text-zinc-100">{stats?.bookings.web_today ?? 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Bu hafta</span>
                  <span className="font-semibold text-zinc-100">{stats?.bookings.web_week ?? 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-zinc-400">Bu ay</span>
                  <span className="font-semibold text-zinc-100">{stats?.bookings.web_month ?? 0}</span>
                </div>
              </div>
            </div>
          </section>

          {/* ── Tenant Bazlı Dağılım ─────────────────────────────────────── */}
          {(stats?.tenant_breakdown.length ?? 0) > 0 && (
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
              <div className="px-4 py-3 border-b border-zinc-800">
                <h2 className="text-sm font-semibold text-zinc-200">Tenant Bazlı Randevu (Bu Ay)</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800 text-left">
                      <th className="px-4 py-2.5 font-medium text-zinc-400">Tenant</th>
                      <th className="px-4 py-2.5 font-medium text-emerald-400 text-right">WhatsApp</th>
                      <th className="px-4 py-2.5 font-medium text-blue-400 text-right">Web</th>
                      <th className="px-4 py-2.5 font-medium text-zinc-400 text-right">Toplam</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats?.tenant_breakdown.map((t) => (
                      <tr key={t.tenant_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                        <td className="px-4 py-2.5 text-zinc-100">{t.tenant_name}</td>
                        <td className="px-4 py-2.5 text-right text-zinc-100">{t.wa_bookings_month}</td>
                        <td className="px-4 py-2.5 text-right text-zinc-100">{t.web_bookings_month}</td>
                        <td className="px-4 py-2.5 text-right font-semibold text-zinc-100">{t.total_bookings_month}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* ── Bot Hata Logu ─────────────────────────────────────────────── */}
          <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
            <div className="px-4 py-3 border-b border-zinc-800 flex flex-wrap items-center gap-2">
              <h2 className="text-sm font-semibold text-zinc-200 mr-auto">Bot Hata Logu</h2>

              {/* Hata tipi filtresi */}
              <select
                value={errType}
                onChange={(e) => { setErrType(e.target.value); setErrPage(1) }}
                className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100"
              >
                <option value="">Tüm tipler</option>
                {ERROR_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>

              {/* Arama */}
              <form onSubmit={(e) => { e.preventDefault(); setErrQ(errSearchInput); setErrPage(1) }}
                className="flex gap-1">
                <input
                  value={errSearchInput}
                  onChange={(e) => setErrSearchInput(e.target.value)}
                  placeholder="Mesaj / numara ara..."
                  className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100 w-40"
                />
                <button type="submit" className="rounded-lg border border-zinc-700 px-2 py-1.5 text-xs text-zinc-300">Ara</button>
                {errQ && (
                  <button type="button" onClick={() => { setErrQ(""); setErrSearchInput(""); setErrPage(1) }}
                    className="text-xs text-zinc-500 hover:text-zinc-300">✕</button>
                )}
              </form>
            </div>

            {!errors || errors.items.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-zinc-500">
                {errors ? "Kayıt bulunamadı." : "Yükleniyor..."}
              </div>
            ) : (
              <>
                <div className="divide-y divide-zinc-800/50">
                  {errors.items.map((err) => (
                    <div key={err.id} className="px-4 py-3 hover:bg-zinc-800/30 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-300">
                          {err.error_type}
                        </span>
                        {err.wa_phone && (
                          <span className="text-xs text-zinc-400">{err.wa_phone}</span>
                        )}
                        <span className="ml-auto text-xs text-zinc-500">{fmt(err.created_at)}</span>
                      </div>
                      <p className="text-sm text-zinc-300 break-all">{err.message}</p>
                    </div>
                  ))}
                </div>

                {/* Sayfalama */}
                {errors.pagination.total_pages > 1 && (
                  <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-3">
                    <p className="text-xs text-zinc-500">
                      Toplam {errors.pagination.total} kayıt — Sayfa {errors.pagination.page}/{errors.pagination.total_pages}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setErrPage((p) => Math.max(1, p - 1))}
                        disabled={errPage <= 1}
                        className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 disabled:opacity-40"
                      >
                        ‹ Önceki
                      </button>
                      <button
                        onClick={() => setErrPage((p) => Math.min(errors.pagination.total_pages, p + 1))}
                        disabled={errPage >= errors.pagination.total_pages}
                        className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 disabled:opacity-40"
                      >
                        Sonraki ›
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </section>
        </>
      )}
    </div>
  )
}
