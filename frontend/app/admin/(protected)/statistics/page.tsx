"use client"

import dynamic from "next/dynamic"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"

const BookingStatusDonut = dynamic(() => import("./BookingStatusDonut"), { ssr: false })
const CustomerTypeDonut = dynamic(() => import("./CustomerTypeDonut"), { ssr: false })
const DailyBookingBar = dynamic(() => import("./DailyBookingBar"), { ssr: false })
const HourlyBookingBar = dynamic(() => import("./HourlyBookingBar"), { ssr: false })

type StatsSummary = {
  start_date: string
  end_date: string
  total_bookings: number
  completed_count: number
  no_show_count: number
  cancelled_count: number
  completion_rate: number
  no_show_rate: number
  cancellation_rate: number
}

type PeriodCustomerStats = {
  start_date: string
  end_date: string
  new_customers: number
  returning_customers: number
}

type NamedStatItem = {
  label: string | null
  value: number
}

type TrendPoint = { label: string; value: number }

type PeriodCapacityStats = {
  start_date: string
  end_date: string
  occupancy_rate: number
  total_capacity_slots: number
  occupied_slots: number
  busiest_day: NamedStatItem
  busiest_hour: NamedStatItem
  bookings_per_day: TrendPoint[]
  bookings_per_hour: TrendPoint[]
}

type RangeStatisticsResponse = {
  start_date: string
  end_date: string
  summary: StatsSummary
  customer_stats: PeriodCustomerStats
  capacity_stats: PeriodCapacityStats
}

type SummaryMetricKey = keyof Pick<
  StatsSummary,
  | "total_bookings"
  | "completed_count"
  | "no_show_count"
  | "cancelled_count"
  | "completion_rate"
  | "no_show_rate"
  | "cancellation_rate"
>

const SUMMARY_CARD_COPY: {
  key: SummaryMetricKey
  title: string
  description: string
  suffix?: "%"
}[] = [
  { key: "total_bookings", title: "Toplam randevu", description: "Secilen donemde olusan tum randevu kayitlari." },
  { key: "completed_count", title: "Tamamlanan", description: "Saati gecmis ve iptal edilmemis randevular." },
  { key: "no_show_count", title: "Gelmeyen", description: "Musteri gelmedi diye isaretlenen randevular." },
  { key: "cancelled_count", title: "Iptal edilen", description: "Iptal edilmis randevularin toplami." },
  { key: "completion_rate", title: "Tamamlanma orani", description: "Toplam randevular icinde tamamlananlarin yuzdesi.", suffix: "%" },
  { key: "no_show_rate", title: "No-show orani", description: "Toplam randevular icinde gelmeyenlerin yuzdesi.", suffix: "%" },
  { key: "cancellation_rate", title: "Iptal orani", description: "Toplam randevular icinde iptal edilenlerin yuzdesi.", suffix: "%" },
] as const

function todayInIstanbulIso(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })
}

function formatDateRange(startDate: string, endDate: string): string {
  const options: Intl.DateTimeFormatOptions = { day: "2-digit", month: "long", year: "numeric", timeZone: "Europe/Istanbul" }
  const startText = new Date(`${startDate}T12:00:00`).toLocaleDateString("tr-TR", options)
  const endText = new Date(`${endDate}T12:00:00`).toLocaleDateString("tr-TR", options)
  if (startDate === endDate) return startText
  return `${startText} - ${endText}`
}

function formatDayLabel(value: string | null): string {
  if (!value) return "Veri yok"
  return new Date(`${value}T12:00:00`).toLocaleDateString("tr-TR", {
    weekday: "long", day: "2-digit", month: "long", timeZone: "Europe/Istanbul",
  })
}

function formatValue(value: number, suffix?: string): string {
  const text = suffix ? value.toFixed(1) : String(value)
  return suffix ? `${text}${suffix}` : text
}

export default function AdminStatisticsPage() {
  const router = useRouter()
  const today = todayInIstanbulIso()
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [stats, setStats] = useState<RangeStatisticsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleApply() {
    if (endDate < startDate) {
      setError("Bitis tarihi baslangic tarihinden once olamaz.")
      return
    }
    setLoading(true)
    setError("")
    try {
      const data = await apiFetch<RangeStatisticsResponse>(
        `/api/v1/admin/statistics/range?start_date=${startDate}&end_date=${endDate}`
      )
      setStats(data)
    } catch (err: unknown) {
      setStats(null)
      setError(err instanceof Error ? err.message : "Istatistikler yuklenemedi.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Menüye dön"
            onClick={() => router.push("/admin/menu")}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-xl leading-none text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800"
          >
            ←
          </button>
          <div>
            <h1 className="text-lg font-bold text-zinc-100">Istatistiklerim</h1>
            <p className="text-xs text-zinc-400">
              {stats ? formatDateRange(stats.start_date, stats.end_date) : "Tarih araligi secin"}
            </p>
          </div>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4">
        <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-xs text-zinc-400">Baslangic Tarihi</label>
              <input
                type="date"
                value={startDate}
                max={endDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="block w-full appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-950 text-zinc-100"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-zinc-400">Bitis Tarihi</label>
              <input
                type="date"
                value={endDate}
                min={startDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="block w-full appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-950 text-zinc-100"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={handleApply}
            className="w-full rounded-lg bg-zinc-100 px-3 py-2.5 text-sm font-semibold text-zinc-900 hover:bg-white"
          >
            Uygula
          </button>
        </section>

        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}

        {loading && (
          <div className="text-sm text-zinc-400 bg-zinc-900 rounded-xl border border-zinc-800 p-4">
            Istatistikler yukleniyor...
          </div>
        )}

        {!loading && !stats && !error && (
          <div className="text-sm text-zinc-400 bg-zinc-900 rounded-xl border border-zinc-800 p-4">
            Istatistikleri gormek icin tarih araligini secip Uygula butonuna basin.
          </div>
        )}

        {!loading && stats && (
          <>
            <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-zinc-100">Randevu ozeti</h2>
                <p className="text-xs text-zinc-500 mt-1">
                  {formatDateRange(stats.summary.start_date, stats.summary.end_date)}
                </p>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {SUMMARY_CARD_COPY.map((item) => (
                  <div key={item.key} className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-zinc-100">{item.title}</p>
                        <p className="text-xs text-zinc-400 mt-1">{item.description}</p>
                      </div>
                      <p className="text-lg font-semibold text-zinc-100">
                        {formatValue(stats.summary[item.key], item.suffix)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <BookingStatusDonut
              completed={stats.summary.completed_count}
              noShow={stats.summary.no_show_count}
              cancelled={stats.summary.cancelled_count}
            />

            <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-zinc-100">Musteri istatistikleri</h2>
                <p className="text-xs text-zinc-400 mt-1">
                  Yeni musteri ilk randevusunu bu donemde alan kisidir. Tekrar gelen musteri ise daha once de kaydi olan kisidir.
                </p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3">
                <p className="text-xs text-zinc-500 mb-3">
                  {formatDateRange(stats.customer_stats.start_date, stats.customer_stats.end_date)}
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-zinc-800 p-3">
                    <p className="text-xs text-zinc-400">Yeni musteri</p>
                    <p className="text-lg font-semibold text-zinc-100 mt-2">{stats.customer_stats.new_customers}</p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 p-3">
                    <p className="text-xs text-zinc-400">Tekrar gelen</p>
                    <p className="text-lg font-semibold text-zinc-100 mt-2">{stats.customer_stats.returning_customers}</p>
                  </div>
                </div>
              </div>
            </section>

            <CustomerTypeDonut
              newCustomers={stats.customer_stats.new_customers}
              returningCustomers={stats.customer_stats.returning_customers}
            />

            <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-zinc-100">Yogunluk ve doluluk</h2>
                <p className="text-xs text-zinc-400 mt-1">
                  Doluluk, uretilen toplam slotlarin kacinda aktif randevu oldugunu gosterir.
                </p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 space-y-3">
                <p className="text-xs text-zinc-500">
                  {formatDateRange(stats.capacity_stats.start_date, stats.capacity_stats.end_date)}
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-zinc-800 p-3">
                    <p className="text-xs text-zinc-400">Doluluk orani</p>
                    <p className="text-lg font-semibold text-zinc-100 mt-2">{stats.capacity_stats.occupancy_rate.toFixed(1)}%</p>
                    <p className="text-xs text-zinc-500 mt-1">
                      {stats.capacity_stats.occupied_slots} / {stats.capacity_stats.total_capacity_slots} slot dolu
                    </p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 p-3">
                    <p className="text-xs text-zinc-400">En yogun gun</p>
                    <p className="text-sm font-semibold text-zinc-100 mt-2">
                      {formatDayLabel(stats.capacity_stats.busiest_day.label)}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{stats.capacity_stats.busiest_day.value} randevu</p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 p-3 col-span-2">
                    <p className="text-xs text-zinc-400">En yogun saat</p>
                    <p className="text-lg font-semibold text-zinc-100 mt-2">
                      {stats.capacity_stats.busiest_hour.label ?? "Veri yok"}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{stats.capacity_stats.busiest_hour.value} randevu</p>
                  </div>
                </div>
              </div>
            </section>

            <DailyBookingBar points={stats.capacity_stats.bookings_per_day} />

            <HourlyBookingBar points={stats.capacity_stats.bookings_per_hour} />
          </>
        )}
      </div>
    </div>
  )
}
