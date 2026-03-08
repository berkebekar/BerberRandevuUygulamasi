/**
 * app/admin/(protected)/settings/page.tsx - Admin ayarlar sayfasi.
 */

"use client"

import { useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { apiDelete, apiFetch, apiPut } from "@/lib/api"

type BarberSettings = {
  slot_duration_minutes: number
  work_start_time: string
  work_end_time: string
  weekly_closed_days: number[]
  max_booking_days_ahead: number
}

type DayOverride = {
  date: string
  is_closed: boolean
  work_start_time: string | null
  work_end_time: string | null
  slot_duration_minutes: number | null
}

const WEEK_DAYS = [
  { label: "Pzt", value: 0 },
  { label: "Sal", value: 1 },
  { label: "Car", value: 2 },
  { label: "Per", value: 3 },
  { label: "Cum", value: 4 },
  { label: "Cmt", value: 5 },
  { label: "Paz", value: 6 },
]

const DURATION_OPTIONS = Array.from({ length: 24 }, (_, i) => (i + 1) * 5)

function todayInIstanbulIso(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })
}

function addDaysIso(isoDate: string, days: number): string {
  const d = new Date(`${isoDate}T12:00:00`)
  d.setDate(d.getDate() + days)
  return d.toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })
}

export default function AdminSettingsPage() {
  const router = useRouter()
  const todayIso = useMemo(() => todayInIstanbulIso(), [])

  // Genel ayarlar
  const [slotDuration, setSlotDuration] = useState(30)
  const [workStart, setWorkStart] = useState("09:00")
  const [workEnd, setWorkEnd] = useState("19:00")
  const [closedDays, setClosedDays] = useState<number[]>([])
  const [maxBookingDaysAhead, setMaxBookingDaysAhead] = useState(14)

  // Ozel gun ayarlari
  const [specialDate, setSpecialDate] = useState(todayIso)
  const [specialIsClosed, setSpecialIsClosed] = useState(false)
  const [specialWorkStart, setSpecialWorkStart] = useState("09:00")
  const [specialWorkEnd, setSpecialWorkEnd] = useState("19:00")
  const [specialSlotDuration, setSpecialSlotDuration] = useState(30)
  const [specialExists, setSpecialExists] = useState(false)
  const [specialLoading, setSpecialLoading] = useState(false)

  // UI state
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  const maxSpecialDate = useMemo(
    () => addDaysIso(todayIso, maxBookingDaysAhead),
    [todayIso, maxBookingDaysAhead]
  )

  const toggleDay = (value: number) => {
    setClosedDays((prev) =>
      prev.includes(value) ? prev.filter((day) => day !== value) : [...prev, value]
    )
  }

  const fillSpecialWithGeneralSettings = (settings?: BarberSettings | null) => {
    const duration = settings?.slot_duration_minutes ?? slotDuration
    const start = (settings?.work_start_time ?? workStart).slice(0, 5)
    const end = (settings?.work_end_time ?? workEnd).slice(0, 5)
    setSpecialIsClosed(false)
    setSpecialWorkStart(start)
    setSpecialWorkEnd(end)
    setSpecialSlotDuration(duration)
  }

  useEffect(() => {
    async function loadSettings() {
      setError("")
      try {
        const data = await apiFetch<BarberSettings | null>("/api/v1/admin/schedule/settings")
        if (data) {
          setSlotDuration(data.slot_duration_minutes)
          setWorkStart(data.work_start_time.slice(0, 5))
          setWorkEnd(data.work_end_time.slice(0, 5))
          setClosedDays(data.weekly_closed_days ?? [])
          setMaxBookingDaysAhead(data.max_booking_days_ahead ?? 14)
          fillSpecialWithGeneralSettings(data)
        } else {
          fillSpecialWithGeneralSettings(null)
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Ayarlar yuklenemedi.")
      }
    }

    loadSettings()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    async function loadSpecialDay() {
      if (!specialDate) return
      setSpecialLoading(true)
      setError("")
      try {
        const data = await apiFetch<DayOverride | null>(
          `/api/v1/admin/schedule/override?date=${specialDate}`
        )
        if (!data) {
          setSpecialExists(false)
          fillSpecialWithGeneralSettings(null)
          return
        }
        setSpecialExists(true)
        setSpecialIsClosed(Boolean(data.is_closed))
        setSpecialWorkStart((data.work_start_time ?? workStart).slice(0, 5))
        setSpecialWorkEnd((data.work_end_time ?? workEnd).slice(0, 5))
        setSpecialSlotDuration(data.slot_duration_minutes ?? slotDuration)
      } catch (err: unknown) {
        setSpecialExists(false)
        setError(err instanceof Error ? err.message : "Ozel gun ayari yuklenemedi.")
      } finally {
        setSpecialLoading(false)
      }
    }

    loadSpecialDay()
  }, [specialDate, slotDuration, workStart, workEnd])

  async function handleSaveSettings() {
    if (!workStart || !workEnd) {
      setError("Baslangic ve bitis saatleri zorunludur.")
      return
    }

    setIsLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiPut("/api/v1/admin/schedule/settings", {
        slot_duration_minutes: slotDuration,
        work_start_time: workStart,
        work_end_time: workEnd,
        weekly_closed_days: closedDays,
        max_booking_days_ahead: maxBookingDaysAhead,
      })
      setSuccess("Ayarlar kaydedildi.")
      if (!specialExists) {
        setSpecialSlotDuration(slotDuration)
        setSpecialWorkStart(workStart)
        setSpecialWorkEnd(workEnd)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kaydetme basarisiz.")
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSaveSpecialDay() {
    if (!specialDate) {
      setError("Ozel gun tarihi secin.")
      return
    }
    if (!specialIsClosed && (!specialWorkStart || !specialWorkEnd)) {
      setError("Acik ozel gun icin baslangic ve bitis saatleri zorunludur.")
      return
    }

    setSpecialLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiPut("/api/v1/admin/schedule/override", {
        date: specialDate,
        is_closed: specialIsClosed,
        work_start_time: specialIsClosed ? null : specialWorkStart,
        work_end_time: specialIsClosed ? null : specialWorkEnd,
        slot_duration_minutes: specialIsClosed ? null : specialSlotDuration,
      })
      setSpecialExists(true)
      setSuccess("Ozel gun kaydedildi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ozel gun kaydedilemedi.")
    } finally {
      setSpecialLoading(false)
    }
  }

  async function handleDeleteSpecialDay() {
    if (!specialDate) return

    setSpecialLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiDelete(`/api/v1/admin/schedule/override?date=${specialDate}`)
      setSpecialExists(false)
      fillSpecialWithGeneralSettings(null)
      setSuccess("Ozel gun kaydi silindi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ozel gun kaydi silinemedi.")
    } finally {
      setSpecialLoading(false)
    }
  }

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
          <h1 className="text-lg font-bold text-zinc-100">Ayarlar</h1>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4 max-w-sm mx-auto">
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3 overflow-hidden">
          <h2 className="text-sm font-semibold text-zinc-200">Calisma Saatleri</h2>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Baslangic</label>
            <input
              type="time"
              value={workStart}
              onChange={(e) => setWorkStart(e.target.value)}
              className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Bitis</label>
            <input
              type="time"
              value={workEnd}
              onChange={(e) => setWorkEnd(e.target.value)}
              className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
            />
          </div>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Randevu Suresi</h2>
          <label className="block text-xs font-medium text-zinc-400 mb-1">Sure secin</label>
          <select
            value={slotDuration}
            onChange={(e) => setSlotDuration(Number(e.target.value))}
            className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900"
          >
            {DURATION_OPTIONS.map((value) => (
              <option key={value} value={value}>
                {value} dk
              </option>
            ))}
          </select>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Ileri Tarih Limiti</h2>
          <label className="block text-xs font-medium text-zinc-400 mb-1">
            Kac gun sonrasina kadar randevu alinabilir?
          </label>
          <select
            value={maxBookingDaysAhead}
            onChange={(e) => setMaxBookingDaysAhead(Number(e.target.value))}
            className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900"
          >
            {Array.from({ length: 60 }, (_, i) => i + 1).map((value) => (
              <option key={value} value={value}>
                {value} gun
              </option>
            ))}
          </select>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Ozel Gun</h2>
          <p className="text-xs text-zinc-400">
            Secili tarihte calisma saati, kapalilik ve slot suresi ayri yonetilir.
          </p>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Tarih</label>
            <input
              type="date"
              value={specialDate}
              min={todayIso}
              max={maxSpecialDate}
              onChange={(e) => setSpecialDate(e.target.value)}
              className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900"
            />
          </div>

          <label className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2.5">
            <span className="text-sm text-zinc-200">Bu gun kapali</span>
            <input
              type="checkbox"
              checked={specialIsClosed}
              onChange={(e) => setSpecialIsClosed(e.target.checked)}
              className="h-4 w-4"
            />
          </label>

          {!specialIsClosed && (
            <>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Baslangic</label>
                <input
                  type="time"
                  value={specialWorkStart}
                  onChange={(e) => setSpecialWorkStart(e.target.value)}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Bitis</label>
                <input
                  type="time"
                  value={specialWorkEnd}
                  onChange={(e) => setSpecialWorkEnd(e.target.value)}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Ozel Gun Slot Suresi
                </label>
                <select
                  value={specialSlotDuration}
                  onChange={(e) => setSpecialSlotDuration(Number(e.target.value))}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900"
                >
                  {DURATION_OPTIONS.map((value) => (
                    <option key={value} value={value}>
                      {value} dk
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handleSaveSpecialDay}
              disabled={specialLoading}
              className="w-full py-2.5 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              {specialLoading ? "Kaydediliyor..." : "Ozel Gunu Kaydet"}
            </button>
            <button
              onClick={handleDeleteSpecialDay}
              disabled={specialLoading || !specialExists}
              className="w-full py-2.5 bg-zinc-800 text-zinc-200 rounded-lg font-medium text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-700 transition-colors"
            >
              Ozel Gunu Sil
            </button>
          </div>
        </div>

        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Izin Gunleri</h2>
          <p className="text-xs text-zinc-400">
            Berberin calismadigi haftanin gunlerini secin. Bu gunlerde slotlar kapali gorunur.
          </p>
          <div className="grid grid-cols-4 gap-2">
            {WEEK_DAYS.map((day) => {
              const isActive = closedDays.includes(day.value)
              return (
                <button
                  key={day.value}
                  type="button"
                  aria-pressed={isActive}
                  onClick={() => toggleDay(day.value)}
                  className={`px-3 py-2 rounded-lg border text-sm font-semibold transition-colors ${
                    isActive
                      ? "bg-emerald-500 text-zinc-950 border-emerald-400"
                      : "bg-zinc-950 text-zinc-300 border-zinc-800 hover:border-zinc-500"
                  }`}
                >
                  {day.label}
                </button>
              )
            })}
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}
        {success && (
          <div className="text-sm text-emerald-300 bg-emerald-500/10 rounded-lg px-3 py-2">
            {success}
          </div>
        )}

        <button
          onClick={handleSaveSettings}
          disabled={isLoading}
          className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
        >
          {isLoading ? "Kaydediliyor..." : "Genel Ayarlari Kaydet"}
        </button>
      </div>
    </div>
  )
}

