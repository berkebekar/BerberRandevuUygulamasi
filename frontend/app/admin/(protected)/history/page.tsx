"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"
import type { BookingHistoryResponse, BookingHistoryStatus } from "../types"
import { BackToMenuButton } from "../BackToMenuButton"
import { BookingHistoryList, SummaryCards, todayInIstanbulIso } from "../history-utils"

const STATUS_OPTIONS: { value: BookingHistoryStatus; label: string }[] = [
  { value: "all", label: "Tümü" },
  { value: "completed", label: "Gerçekleşen" },
  { value: "upcoming", label: "Yaklaşan" },
  { value: "cancelled", label: "İptal" },
  { value: "no_show", label: "Gelmedi" },
]

export default function AdminBookingHistoryPage() {
  const router = useRouter()
  const today = todayInIstanbulIso()
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [status, setStatus] = useState<BookingHistoryStatus>("all")
  const [pageSize, setPageSize] = useState(10)
  const [page, setPage] = useState(1)
  const [data, setData] = useState<BookingHistoryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function load(nextPage = 1) {
    setLoading(true)
    setError("")
    try {
      const result = await apiFetch<BookingHistoryResponse>(
        `/api/v1/admin/bookings/history?start_date=${startDate}&end_date=${endDate}&status=${status}&page=${nextPage}&page_size=${pageSize}`
      )
      setData(result)
      setPage(nextPage)
    } catch (err: unknown) {
      setData(null)
      setError(err instanceof Error ? err.message : "Randevu gecmisi yuklenemedi.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 px-4 py-4">
        <div className="flex items-center gap-3">
          <BackToMenuButton />
          <h1 className="text-lg font-bold text-zinc-100">Randevu Geçmişim</h1>
        </div>
      </div>

      <div className="space-y-4 px-4 pt-5">
        <section className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="min-w-0 space-y-1 text-xs text-zinc-400">
              Başlangıç
              <input type="date" value={startDate} max={endDate} onChange={(e) => setStartDate(e.target.value)} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
            </label>
            <label className="min-w-0 space-y-1 text-xs text-zinc-400">
              Bitiş
              <input type="date" value={endDate} min={startDate} onChange={(e) => setEndDate(e.target.value)} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100" />
            </label>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="min-w-0 space-y-1 text-xs text-zinc-400">
              Durum
              <select value={status} onChange={(e) => setStatus(e.target.value as BookingHistoryStatus)} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100">
                {STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <label className="min-w-0 space-y-1 text-xs text-zinc-400">
              Liste
              <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))} className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100">
                {[10, 25, 50].map((value) => <option key={value} value={value}>{value}</option>)}
              </select>
            </label>
          </div>
          <button type="button" onClick={() => load(1)} disabled={loading} className="w-full rounded-lg bg-zinc-100 px-3 py-2.5 text-sm font-semibold text-zinc-950 disabled:opacity-60">
            {loading ? "Yukleniyor..." : "Uygula"}
          </button>
        </section>

        {error && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}
        {data && <SummaryCards stats={data.summary} />}
        {data && <BookingHistoryList items={data.items} />}
        {data && data.pagination.total_pages > 1 && (
          <div className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 p-3">
            <button disabled={page <= 1 || loading} onClick={() => load(page - 1)} className="text-sm text-zinc-300 disabled:text-zinc-600">Önceki</button>
            <span className="text-xs text-zinc-500">{page} / {data.pagination.total_pages}</span>
            <button disabled={page >= data.pagination.total_pages || loading} onClick={() => load(page + 1)} className="text-sm text-zinc-300 disabled:text-zinc-600">Sonraki</button>
          </div>
        )}
      </div>
    </div>
  )
}
