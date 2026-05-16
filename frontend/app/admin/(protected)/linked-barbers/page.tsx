"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import type { BookingHistoryResponse } from "../types"
import { BookingHistoryList, SummaryCards, todayInIstanbulIso } from "../history-utils"

type LinkedTenant = {
  id: string
  first_name: string | null
  last_name: string | null
  name: string
}

type LinkedOverview = {
  mode: "owner" | "child"
  linked_tenants: LinkedTenant[]
  parent_tenant: {
    id: string
    name: string
    first_name: string | null
    last_name: string | null
  } | null
}

function barberName(item: LinkedTenant | NonNullable<LinkedOverview["parent_tenant"]>): string {
  const fullName = `${item.first_name ?? ""} ${item.last_name ?? ""}`.trim()
  return fullName || item.name
}

export default function LinkedBarbersPage() {
  const router = useRouter()
  const today = todayInIstanbulIso()
  const [overview, setOverview] = useState<LinkedOverview | null>(null)
  const [selectedTenantId, setSelectedTenantId] = useState("")
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [pageSize, setPageSize] = useState(10)
  const [page, setPage] = useState(1)
  const [data, setData] = useState<BookingHistoryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    async function loadOverview() {
      setLoading(true)
      setError("")
      try {
        const result = await apiFetch<LinkedOverview>("/api/v1/admin/linked-tenants")
        setOverview(result)
        setSelectedTenantId(result.linked_tenants[0]?.id ?? "")
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Bagli berberler yuklenemedi.")
      } finally {
        setLoading(false)
      }
    }
    loadOverview()
  }, [])

  async function loadHistory(nextPage = 1) {
    if (!selectedTenantId) return
    setLoading(true)
    setError("")
    try {
      const result = await apiFetch<BookingHistoryResponse>(
        `/api/v1/admin/linked-tenants/${selectedTenantId}/bookings?start_date=${startDate}&end_date=${endDate}&page=${nextPage}&page_size=${pageSize}`
      )
      setData(result)
      setPage(nextPage)
    } catch (err: unknown) {
      setData(null)
      setError(err instanceof Error ? err.message : "Randevular yuklenemedi.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 px-4 py-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Menüye dön"
            onClick={() => router.push("/admin/menu")}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-xl leading-none text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800"
          >
            ←
          </button>
          <h1 className="text-lg font-bold text-zinc-100">Çalışan Berberler</h1>
        </div>
      </div>

      <div className="space-y-4 px-4 pt-5">
        {loading && !overview && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-400">Yukleniyor...</div>
        )}
        {error && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

        {overview?.mode === "child" && (
          <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
            <p className="text-sm font-semibold text-zinc-100">
              {overview.parent_tenant ? `${barberName(overview.parent_tenant)} salonuna bağlı çalışıyorsunuz.` : "Bir salona bağlı çalışıyorsunuz."}
            </p>
            <p className="mt-2 text-sm text-zinc-400">Bu salondan ayrılmak için bbsoftla iletişime geçin.</p>
          </section>
        )}

        {overview?.mode === "owner" && overview.linked_tenants.length === 0 && (
          <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-400">
            Size bağlı çalışan bir berber yok.
          </section>
        )}

        {overview?.mode === "owner" && overview.linked_tenants.length > 0 && (
          <>
            <section className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
              <label className="space-y-1 text-xs text-zinc-400">
                Berber
                <select value={selectedTenantId} onChange={(e) => { setSelectedTenantId(e.target.value); setData(null); }} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100">
                  {overview.linked_tenants.map((item) => (
                    <option key={item.id} value={item.id}>{barberName(item)}</option>
                  ))}
                </select>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-1 text-xs text-zinc-400">
                  Başlangıç
                  <input type="date" value={startDate} max={endDate} onChange={(e) => setStartDate(e.target.value)} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
                </label>
                <label className="space-y-1 text-xs text-zinc-400">
                  Bitiş
                  <input type="date" value={endDate} min={startDate} onChange={(e) => setEndDate(e.target.value)} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
                </label>
              </div>
              <label className="space-y-1 text-xs text-zinc-400">
                Liste
                <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100">
                  {[10, 25, 50].map((value) => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <button type="button" onClick={() => loadHistory(1)} disabled={loading} className="w-full rounded-lg bg-zinc-100 px-3 py-2.5 text-sm font-semibold text-zinc-950 disabled:opacity-60">
                {loading ? "Yukleniyor..." : "Uygula"}
              </button>
            </section>

            {data && <SummaryCards stats={data.summary} />}
            {data && <BookingHistoryList items={data.items} />}
            {data && data.pagination.total_pages > 1 && (
              <div className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 p-3">
                <button disabled={page <= 1 || loading} onClick={() => loadHistory(page - 1)} className="text-sm text-zinc-300 disabled:text-zinc-600">Önceki</button>
                <span className="text-xs text-zinc-500">{page} / {data.pagination.total_pages}</span>
                <button disabled={page >= data.pagination.total_pages || loading} onClick={() => loadHistory(page + 1)} className="text-sm text-zinc-300 disabled:text-zinc-600">Sonraki</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
