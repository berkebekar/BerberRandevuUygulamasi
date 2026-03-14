"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"

type SummaryStats = {
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

type SummaryMetricKey = keyof Pick<
  SummaryStats,
  | "total_bookings"
  | "completed_count"
  | "no_show_count"
  | "cancelled_count"
  | "completion_rate"
  | "no_show_rate"
  | "cancellation_rate"
>

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

type PeriodCapacityStats = {
  start_date: string
  end_date: string
  occupancy_rate: number
  total_capacity_slots: number
  occupied_slots: number
  busiest_day: NamedStatItem
  busiest_hour: NamedStatItem
}

type StatisticsResponse = {
  selected_date: string
  daily_summary: SummaryStats
  weekly_summary: SummaryStats
  monthly_summary: SummaryStats
  customer_stats: {
    daily: PeriodCustomerStats
    weekly: PeriodCustomerStats
    monthly: PeriodCustomerStats
  }
  capacity_stats: {
    daily: PeriodCapacityStats
    weekly: PeriodCapacityStats
    monthly: PeriodCapacityStats
  }
}

type PeriodTab = "daily" | "weekly" | "monthly"

const SUMMARY_CARD_COPY: {
  key: SummaryMetricKey
  title: string
  description: string
  suffix?: "%"
}[] = [
  {
    key: "total_bookings",
    title: "Toplam randevu",
    description: "Secilen donemde olusan tum randevu kayitlari.",
  },
  {
    key: "completed_count",
    title: "Tamamlanan",
    description: "Saati gecmis ve iptal edilmemis randevular.",
  },
  {
    key: "no_show_count",
    title: "Gelmeyen",
    description: "Musteri gelmedi diye isaretlenen randevular.",
  },
  {
    key: "cancelled_count",
    title: "Iptal edilen",
    description: "Iptal edilmis randevularin toplami.",
  },
  {
    key: "completion_rate",
    title: "Tamamlanma orani",
    description: "Toplam randevular icinde tamamlananlarin yuzdesi.",
    suffix: "%",
  },
  {
    key: "no_show_rate",
    title: "No-show orani",
    description: "Toplam randevular icinde gelmeyenlerin yuzdesi.",
    suffix: "%",
  },
  {
    key: "cancellation_rate",
    title: "Iptal orani",
    description: "Toplam randevular icinde iptal edilenlerin yuzdesi.",
    suffix: "%",
  },
] as const

const PERIOD_TABS: { key: PeriodTab; label: string }[] = [
  { key: "daily", label: "Gunluk" },
  { key: "weekly", label: "Haftalik" },
  { key: "monthly", label: "Aylik" },
]

function todayInIstanbulIso(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })
}

function formatDateRange(startDate: string, endDate: string): string {
  const options: Intl.DateTimeFormatOptions = {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "Europe/Istanbul",
  }
  const startText = new Date(`${startDate}T12:00:00`).toLocaleDateString("tr-TR", options)
  const endText = new Date(`${endDate}T12:00:00`).toLocaleDateString("tr-TR", options)
  return `${startText} - ${endText}`
}

function formatDayLabel(value: string | null): string {
  if (!value) return "Veri yok"
  return new Date(`${value}T12:00:00`).toLocaleDateString("tr-TR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    timeZone: "Europe/Istanbul",
  })
}

function formatValue(value: number, suffix?: string): string {
  const text = suffix ? value.toFixed(1) : String(value)
  return suffix ? `${text}${suffix}` : text
}

function PeriodTabs({
  value,
  onChange,
}: {
  value: PeriodTab
  onChange: (tab: PeriodTab) => void
}) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {PERIOD_TABS.map((tab) => {
        const isActive = tab.key === value
        return (
          <button
            key={tab.key}
            type="button"
            onClick={() => onChange(tab.key)}
            className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
              isActive
                ? "bg-zinc-100 text-zinc-950 border-zinc-100"
                : "bg-zinc-950 text-zinc-300 border-zinc-800 hover:border-zinc-500"
            }`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}

function SummarySection({
  title,
  period,
  onPeriodChange,
  stats,
}: {
  title: string
  period: PeriodTab
  onPeriodChange: (tab: PeriodTab) => void
  stats: SummaryStats
}) {
  return (
    <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">{title}</h2>
        <p className="text-xs text-zinc-500 mt-1">
          {formatDateRange(stats.start_date, stats.end_date)}
        </p>
      </div>
      <PeriodTabs value={period} onChange={onPeriodChange} />
      <div className="grid grid-cols-1 gap-3">
        {SUMMARY_CARD_COPY.map((item) => (
          <div key={item.key} className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-zinc-100">{item.title}</p>
                <p className="text-xs text-zinc-400 mt-1">{item.description}</p>
              </div>
              <p className="text-lg font-semibold text-zinc-100">
                {formatValue(stats[item.key], item.suffix)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function CustomerSection({
  period,
  onPeriodChange,
  stats,
}: {
  period: PeriodTab
  onPeriodChange: (tab: PeriodTab) => void
  stats: StatisticsResponse["customer_stats"]
}) {
  const currentStats = stats[period]

  return (
    <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">Musteri istatistikleri</h2>
        <p className="text-xs text-zinc-400 mt-1">
          Yeni musteri ilk randevusunu bu donemde alan kisidir. Tekrar gelen musteri ise daha once de kaydi olan kisidir.
        </p>
      </div>
      <PeriodTabs value={period} onChange={onPeriodChange} />
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 space-y-3">
        <div>
          <p className="text-sm font-medium text-zinc-100">
            {PERIOD_TABS.find((tab) => tab.key === period)?.label}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            {formatDateRange(currentStats.start_date, currentStats.end_date)}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-zinc-800 p-3">
            <p className="text-xs text-zinc-400">Yeni musteri</p>
            <p className="text-lg font-semibold text-zinc-100 mt-2">{currentStats.new_customers}</p>
          </div>
          <div className="rounded-lg border border-zinc-800 p-3">
            <p className="text-xs text-zinc-400">Tekrar gelen</p>
            <p className="text-lg font-semibold text-zinc-100 mt-2">{currentStats.returning_customers}</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function CapacitySection({
  period,
  onPeriodChange,
  stats,
}: {
  period: PeriodTab
  onPeriodChange: (tab: PeriodTab) => void
  stats: StatisticsResponse["capacity_stats"]
}) {
  const currentStats = stats[period]

  return (
    <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-100">Yogunluk ve doluluk</h2>
        <p className="text-xs text-zinc-400 mt-1">
          Doluluk, uretilen toplam slotlarin kacinda aktif randevu oldugunu gosterir.
        </p>
      </div>
      <PeriodTabs value={period} onChange={onPeriodChange} />
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/70 p-3 space-y-3">
        <div>
          <p className="text-sm font-medium text-zinc-100">
            {PERIOD_TABS.find((tab) => tab.key === period)?.label}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            {formatDateRange(currentStats.start_date, currentStats.end_date)}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-zinc-800 p-3">
            <p className="text-xs text-zinc-400">Doluluk orani</p>
            <p className="text-lg font-semibold text-zinc-100 mt-2">{currentStats.occupancy_rate.toFixed(1)}%</p>
            <p className="text-xs text-zinc-500 mt-1">
              {currentStats.occupied_slots} / {currentStats.total_capacity_slots} slot dolu
            </p>
          </div>
          <div className="rounded-lg border border-zinc-800 p-3">
            <p className="text-xs text-zinc-400">En yogun gun</p>
            <p className="text-sm font-semibold text-zinc-100 mt-2">
              {formatDayLabel(currentStats.busiest_day.label)}
            </p>
            <p className="text-xs text-zinc-500 mt-1">{currentStats.busiest_day.value} randevu</p>
          </div>
          <div className="rounded-lg border border-zinc-800 p-3 col-span-2">
            <p className="text-xs text-zinc-400">En yogun saat</p>
            <p className="text-lg font-semibold text-zinc-100 mt-2">
              {currentStats.busiest_hour.label ?? "Veri yok"}
            </p>
            <p className="text-xs text-zinc-500 mt-1">{currentStats.busiest_hour.value} randevu</p>
          </div>
        </div>
      </div>
    </section>
  )
}

export default function AdminStatisticsPage() {
  const router = useRouter()
  const [selectedDate, setSelectedDate] = useState(() => todayInIstanbulIso())
  const [stats, setStats] = useState<StatisticsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [summaryPeriod, setSummaryPeriod] = useState<PeriodTab>("daily")
  const [customerPeriod, setCustomerPeriod] = useState<PeriodTab>("daily")
  const [capacityPeriod, setCapacityPeriod] = useState<PeriodTab>("daily")

  useEffect(() => {
    let active = true

    async function loadStatistics() {
      setLoading(true)
      setError("")
      try {
        const data = await apiFetch<StatisticsResponse>(`/api/v1/admin/statistics?date=${selectedDate}`)
        if (!active) return
        setStats(data)
      } catch (err: unknown) {
        if (!active) return
        setStats(null)
        setError(err instanceof Error ? err.message : "Istatistikler yuklenemedi.")
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadStatistics()
    return () => {
      active = false
    }
  }, [selectedDate])

  const headerText = useMemo(() => {
    if (!stats) return "Secilen tarihe gore gunluk, haftalik ve aylik performansinizi gorun."
    return `Secilen tarih: ${formatDateRange(stats.selected_date, stats.selected_date)}`
  }, [stats])

  const activeSummary = useMemo(() => {
    if (!stats) return null
    return stats[`${summaryPeriod}_summary` as const]
  }, [stats, summaryPeriod])

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/admin")}
            className="text-zinc-400 hover:text-zinc-300 text-sm"
          >
            {"<- Geri"}
          </button>
          <div>
            <h1 className="text-lg font-bold text-zinc-100">Istatistiklerim</h1>
            <p className="text-xs text-zinc-400">{headerText}</p>
          </div>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4">
        <section className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-zinc-100">Tarih secimi</h2>
            <p className="text-xs text-zinc-400 mt-1">
              Sectiginiz tarih gunluk, haftalik ve aylik ozetlerin referans noktasi olur.
            </p>
          </div>
          <input
            type="date"
            value={selectedDate}
            onChange={(event) => setSelectedDate(event.target.value)}
            className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-950 text-zinc-100"
          />
        </section>

        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}

        {loading && (
          <div className="text-sm text-zinc-400 bg-zinc-900 rounded-xl border border-zinc-800 p-4">
            Istatistikler yukleniyor...
          </div>
        )}

        {!loading && stats && (
          <>
            {activeSummary && (
              <SummarySection
                title="Randevu ozeti"
                period={summaryPeriod}
                onPeriodChange={setSummaryPeriod}
                stats={activeSummary}
              />
            )}
            <CustomerSection
              period={customerPeriod}
              onPeriodChange={setCustomerPeriod}
              stats={stats.customer_stats}
            />
            <CapacitySection
              period={capacityPeriod}
              onPeriodChange={setCapacityPeriod}
              stats={stats.capacity_stats}
            />
          </>
        )}
      </div>
    </div>
  )
}
