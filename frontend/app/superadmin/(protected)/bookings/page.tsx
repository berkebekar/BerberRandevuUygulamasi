"use client"

import { useCallback, useEffect, useState } from "react"
import { SuperAdminApiError, superAdminGet } from "@/lib/superadmin-api"

// ─── Tipler ───────────────────────────────────────────────────────────────────

type BookingItem = {
  id: string
  tenant_id: string
  tenant_name: string
  user_id: string
  customer_name: string
  customer_phone: string
  slot_time: string
  status: string
  cancelled_by: string | null
  source: string
  created_at: string
}

type BookingListResponse = {
  items: BookingItem[]
  pagination: { page: number; page_size: number; total: number; total_pages: number }
}

type TenantOption = { id: string; name: string }

// ─── Yardımcılar ──────────────────────────────────────────────────────────────

function fmt(dt: string) {
  return new Date(dt).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  })
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    confirmed: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
    cancelled: "border-red-500/40 bg-red-500/10 text-red-300",
    no_show: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  }
  const label: Record<string, string> = {
    confirmed: "Onaylı",
    cancelled: "İptal",
    no_show: "Gelmedi",
  }
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${map[status] ?? "border-zinc-700 bg-zinc-800 text-zinc-300"}`}>
      {label[status] ?? status}
    </span>
  )
}

function SourceBadge({ source }: { source: string }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${
      source === "whatsapp"
        ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
        : "border-blue-500/40 bg-blue-500/10 text-blue-300"
    }`}>
      {source === "whatsapp" ? "WhatsApp" : "Web"}
    </span>
  )
}

// ─── Sayfa ────────────────────────────────────────────────────────────────────

export default function SuperAdminBookingsPage() {
  const [data, setData] = useState<BookingListResponse | null>(null)
  const [tenants, setTenants] = useState<TenantOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // Filtreler
  const [tenantId, setTenantId] = useState("")
  const [status, setStatus] = useState("")
  const [source, setSource] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [q, setQ] = useState("")
  const [page, setPage] = useState(1)

  // Tenant listesini bir kez çek (filtre dropdown'u için)
  useEffect(() => {
    superAdminGet<{ items: Array<{ id: string; name: string; first_name?: string; last_name?: string }> }>(
      "/api/v1/superadmin/tenants?page=1&page_size=200"
    )
      .then((res) => {
        setTenants(
          res.items.map((t) => {
            const fn = (t.first_name ?? "").trim()
            const ln = (t.last_name ?? "").trim()
            const display = fn || ln ? `${fn} ${ln}`.trim() : t.name
            return { id: t.id, name: display }
          })
        )
      })
      .catch(() => {})
  }, [])

  const fetchBookings = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "50" })
      if (tenantId) params.set("tenant_id", tenantId)
      if (status) params.set("status", status)
      if (source) params.set("source", source)
      if (dateFrom) params.set("date_from", dateFrom)
      if (dateTo) params.set("date_to", dateTo)
      if (q) params.set("q", q)
      const res = await superAdminGet<BookingListResponse>(`/api/v1/superadmin/bookings?${params}`)
      setData(res)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Randevular yüklenemedi.")
    } finally {
      setLoading(false)
    }
  }, [page, tenantId, status, source, dateFrom, dateTo, q])

  useEffect(() => { fetchBookings() }, [fetchBookings])

  function resetFilters() {
    setTenantId("")
    setStatus("")
    setSource("")
    setDateFrom("")
    setDateTo("")
    setSearchInput("")
    setQ("")
    setPage(1)
  }

  const hasFilters = tenantId || status || source || dateFrom || dateTo || q

  return (
    <div className="space-y-5">

      {/* Başlık */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-zinc-100">Randevular</h1>
            <p className="mt-1 text-sm text-zinc-400">
              Tüm tenant'lara ait randevular.
              {data && (
                <span className="ml-2 text-zinc-500">
                  Toplam {data.pagination.total} kayıt
                </span>
              )}
            </p>
          </div>
          <button
            onClick={() => { setPage(1); fetchBookings() }}
            className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-100 hover:bg-zinc-800/50"
          >
            Yenile
          </button>
        </div>
      </section>

      {/* Filtreler */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div className="flex flex-wrap gap-3">
          {/* Tenant */}
          <select
            value={tenantId}
            onChange={(e) => { setTenantId(e.target.value); setPage(1) }}
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100 min-w-[140px]"
          >
            <option value="">Tüm tenantlar</option>
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>

          {/* Durum */}
          <select
            value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1) }}
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100"
          >
            <option value="">Tüm durumlar</option>
            <option value="confirmed">Onaylı</option>
            <option value="cancelled">İptal</option>
            <option value="no_show">Gelmedi</option>
          </select>

          {/* Kaynak */}
          <select
            value={source}
            onChange={(e) => { setSource(e.target.value); setPage(1) }}
            className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100"
          >
            <option value="">Tüm kaynaklar</option>
            <option value="web">Web</option>
            <option value="whatsapp">WhatsApp</option>
          </select>

          {/* Tarih aralığı */}
          <div className="flex items-center gap-1.5">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100"
            />
            <span className="text-xs text-zinc-500">–</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100"
            />
          </div>

          {/* Arama */}
          <form
            onSubmit={(e) => { e.preventDefault(); setQ(searchInput); setPage(1) }}
            className="flex gap-1"
          >
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Müşteri adı / telefon..."
              className="rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-xs text-zinc-100 w-44"
            />
            <button type="submit" className="rounded-lg border border-zinc-700 px-2 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800/50">
              Ara
            </button>
          </form>

          {hasFilters && (
            <button
              onClick={resetFilters}
              className="text-xs text-zinc-500 hover:text-zinc-300 px-1"
            >
              Filtreleri temizle ✕
            </button>
          )}
        </div>
      </section>

      {error && (
        <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>
      )}

      {/* Tablo */}
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 overflow-hidden">
        {loading ? (
          <div className="space-y-2 p-4">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-zinc-800/70" />
            ))}
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-zinc-500">
            {data ? "Kayıt bulunamadı." : "Yükleniyor..."}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-left">
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Tenant</th>
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Müşteri</th>
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Telefon</th>
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Randevu Zamanı</th>
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Durum</th>
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Kaynak</th>
                    <th className="px-4 py-2.5 font-medium text-zinc-400">Oluşturulma</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                      <td className="px-4 py-2.5 text-zinc-300 text-xs">{item.tenant_name}</td>
                      <td className="px-4 py-2.5 text-zinc-100 font-medium">{item.customer_name}</td>
                      <td className="px-4 py-2.5 text-zinc-400 font-mono text-xs">{item.customer_phone}</td>
                      <td className="px-4 py-2.5 text-zinc-100 whitespace-nowrap">{fmt(item.slot_time)}</td>
                      <td className="px-4 py-2.5">
                        <StatusBadge status={item.status} />
                      </td>
                      <td className="px-4 py-2.5">
                        <SourceBadge source={item.source} />
                      </td>
                      <td className="px-4 py-2.5 text-zinc-500 text-xs whitespace-nowrap">{fmt(item.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Sayfalama */}
            {data.pagination.total_pages > 1 && (
              <div className="flex items-center justify-between border-t border-zinc-800 px-4 py-3">
                <p className="text-xs text-zinc-500">
                  Toplam {data.pagination.total} kayıt — Sayfa {data.pagination.page}/{data.pagination.total_pages}
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 disabled:opacity-40 hover:bg-zinc-800/50"
                  >
                    ‹ Önceki
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(data.pagination.total_pages, p + 1))}
                    disabled={page >= data.pagination.total_pages}
                    className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-300 disabled:opacity-40 hover:bg-zinc-800/50"
                  >
                    Sonraki ›
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
