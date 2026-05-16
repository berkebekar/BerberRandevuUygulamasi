"use client"

import type { BookingHistoryItem, BookingHistoryResponse } from "./types"

export function todayInIstanbulIso(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("tr-TR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  })
}

export function statusText(item: BookingHistoryItem): string {
  if (item.status === "cancelled") return "Iptal"
  if (item.status === "no_show") return "Gelmedi"
  return new Date(item.slot_time).getTime() <= Date.now() ? "Gerceklesti" : "Yaklasan"
}

export function cancelledByText(value?: BookingHistoryItem["cancelled_by"]): string {
  if (value === "admin") return "Berber"
  if (value === "user") return "Musteri"
  if (value === "rescheduled_by_user") return "Musteri saat degistirdi"
  if (value === "rescheduled_by_admin") return "Berber saat degistirdi"
  return "-"
}

export function SummaryCards({ stats }: { stats: BookingHistoryResponse["summary"] }) {
  const cards = [
    ["Toplam", stats.total_bookings],
    ["Gerceklesen", stats.completed_count],
    ["Yaklasan", stats.upcoming_count],
    ["Iptal", stats.cancelled_count],
    ["Gelmedi", stats.no_show_count],
  ] as const
  return (
    <div className="grid grid-cols-2 gap-2">
      {cards.map(([label, value]) => (
        <div key={label} className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
          <p className="text-xs text-zinc-500">{label}</p>
          <p className="mt-1 text-xl font-semibold text-zinc-100">{value}</p>
        </div>
      ))}
    </div>
  )
}

export function BookingHistoryList({ items }: { items: BookingHistoryItem[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-400">
        Secilen aralikta randevu bulunamadi.
      </div>
    )
  }
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <article key={item.id} className="rounded-lg border border-zinc-800 bg-zinc-900 p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-zinc-100">{formatDateTime(item.slot_time)}</p>
              <p className="mt-1 text-sm text-zinc-200 break-words">
                {item.user_first_name} {item.user_last_name}
              </p>
              <p className="text-xs text-zinc-400 break-all">{item.user_phone}</p>
            </div>
            <span className="shrink-0 rounded-full border border-zinc-700 px-2 py-1 text-xs text-zinc-300">
              {statusText(item)}
            </span>
          </div>
          <dl className="mt-3 grid grid-cols-1 gap-1 text-xs text-zinc-400">
            <div className="flex justify-between gap-3">
              <dt>Iptal eden</dt>
              <dd className="text-right text-zinc-300">{cancelledByText(item.cancelled_by)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>Olusturulma</dt>
              <dd className="text-right text-zinc-300">{formatDateTime(item.created_at)}</dd>
            </div>
          </dl>
        </article>
      ))}
    </div>
  )
}
