/**
 * app/admin/(protected)/settings/page.tsx - Admin ayarlar sayfasi.
 */

"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { usePathname, useRouter } from "next/navigation"
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

type AdminProfile = {
  first_name: string | null
  last_name: string | null
  business_name: string
  business_address: string | null
  phone: string
  email: string
}

type SettingsSection = "business" | "personal" | "whatsapp"

const SETTINGS_SECTION_PATHS: Record<SettingsSection, string> = {
  business: "/admin/settings/business",
  personal: "/admin/settings/personal",
  whatsapp: "/admin/settings/whatsapp",
}

const SETTINGS_SECTION_LABELS: Record<SettingsSection, string> = {
  business: "İşletme Ayarları",
  personal: "Kişisel Ayarlar",
  whatsapp: "Whatsapp Bot Ayarları",
}

function sectionFromPath(pathname: string): SettingsSection | null {
  const section = pathname.split("/").filter(Boolean).at(-1)
  return section === "business" || section === "personal" || section === "whatsapp" ? section : null
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
  const pathname = usePathname()
  const todayIso = useMemo(() => todayInIstanbulIso(), [])
  const activeSection = useMemo(() => sectionFromPath(pathname), [pathname])

  // Genel ayarlar
  const [slotDuration, setSlotDuration] = useState(30)
  const [workStart, setWorkStart] = useState("09:00")
  const [workEnd, setWorkEnd] = useState("19:00")
  const [closedDays, setClosedDays] = useState<number[]>([])
  const [maxBookingDaysAhead, setMaxBookingDaysAhead] = useState(14)

  // Ozel gun ayarlari
  const [specialDate, setSpecialDate] = useState(todayIso)
  const [specialWorkStart, setSpecialWorkStart] = useState("09:00")
  const [specialWorkEnd, setSpecialWorkEnd] = useState("19:00")
  const [specialSlotDuration, setSpecialSlotDuration] = useState(30)
  const [specialExists, setSpecialExists] = useState(false)
  const [specialLoading, setSpecialLoading] = useState(false)
  const [closeDate, setCloseDate] = useState(todayIso)
  const [closeExists, setCloseExists] = useState(false)
  const [closeLoading, setCloseLoading] = useState(false)

  // UI state
  const [isLoading, setIsLoading] = useState(false)
  const [profileLoading, setProfileLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [businessName, setBusinessName] = useState("")
  const [businessAddress, setBusinessAddress] = useState("")
  const [adminPhone, setAdminPhone] = useState("")
  const [adminEmail, setAdminEmail] = useState("")
  const generalDefaultsRef = useRef({
    slotDuration: 30,
    workStart: "09:00",
    workEnd: "19:00",
  })

  const maxSpecialDate = useMemo(
    () => addDaysIso(todayIso, maxBookingDaysAhead),
    [todayIso, maxBookingDaysAhead]
  )

  const toggleDay = (value: number) => {
    setClosedDays((prev) =>
      prev.includes(value) ? prev.filter((day) => day !== value) : [...prev, value]
    )
  }

  const fillSpecialWithGeneralSettings = useCallback((settings?: BarberSettings | null) => {
      const duration = settings?.slot_duration_minutes ?? slotDuration
      const start = (settings?.work_start_time ?? workStart).slice(0, 5)
      const end = (settings?.work_end_time ?? workEnd).slice(0, 5)
      setSpecialWorkStart(start)
      setSpecialWorkEnd(end)
      setSpecialSlotDuration(duration)
    }, [slotDuration, workStart, workEnd])

  useEffect(() => {
    generalDefaultsRef.current = {
      slotDuration,
      workStart,
      workEnd,
    }
  }, [slotDuration, workStart, workEnd])

  useEffect(() => {
    async function loadSettings() {
      setError("")
      try {
        const data = await apiFetch<BarberSettings | null>("/api/v1/admin/schedule/settings")
        if (data) {
          const nextSlotDuration = data.slot_duration_minutes
          const nextWorkStart = data.work_start_time.slice(0, 5)
          const nextWorkEnd = data.work_end_time.slice(0, 5)
          setSlotDuration(nextSlotDuration)
          setWorkStart(nextWorkStart)
          setWorkEnd(nextWorkEnd)
          setClosedDays(data.weekly_closed_days ?? [])
          setMaxBookingDaysAhead(data.max_booking_days_ahead ?? 14)
          setSpecialWorkStart(nextWorkStart)
          setSpecialWorkEnd(nextWorkEnd)
          setSpecialSlotDuration(nextSlotDuration)
        } else {
          setSpecialWorkStart("09:00")
          setSpecialWorkEnd("19:00")
          setSpecialSlotDuration(30)
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Ayarlar yuklenemedi.")
      }
    }

    loadSettings()
  }, [])

  useEffect(() => {
    async function loadProfile() {
      setProfileLoading(true)
      setError("")
      try {
        const data = await apiFetch<AdminProfile>("/api/v1/admin/profile")
        setFirstName(data.first_name ?? "")
        setLastName(data.last_name ?? "")
        setBusinessName(data.business_name ?? "")
        setBusinessAddress(data.business_address ?? "")
        setAdminPhone(data.phone ?? "")
        setAdminEmail(data.email ?? "")
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Profil bilgileri yuklenemedi.")
      } finally {
        setProfileLoading(false)
      }
    }

    loadProfile()
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
        if (data.is_closed) {
          setSpecialExists(false)
          fillSpecialWithGeneralSettings(null)
          return
        }
        setSpecialExists(true)
        const general = generalDefaultsRef.current
        setSpecialWorkStart((data.work_start_time ?? general.workStart).slice(0, 5))
        setSpecialWorkEnd((data.work_end_time ?? general.workEnd).slice(0, 5))
        setSpecialSlotDuration(data.slot_duration_minutes ?? general.slotDuration)
      } catch (err: unknown) {
        setSpecialExists(false)
        setError(err instanceof Error ? err.message : "Ozel gun ayari yuklenemedi.")
      } finally {
        setSpecialLoading(false)
      }
    }

    loadSpecialDay()
  }, [fillSpecialWithGeneralSettings, specialDate])

  useEffect(() => {
    async function loadCloseDay() {
      if (!closeDate) return
      setCloseLoading(true)
      setError("")
      try {
        const data = await apiFetch<DayOverride | null>(
          `/api/v1/admin/schedule/override?date=${closeDate}`
        )
        setCloseExists(Boolean(data?.is_closed))
      } catch (err: unknown) {
        setCloseExists(false)
        setError(err instanceof Error ? err.message : "Gun kapatma ayari yuklenemedi.")
      } finally {
        setCloseLoading(false)
      }
    }

    loadCloseDay()
  }, [closeDate])

  async function handleSaveSettings() {
    if (!businessName.trim()) {
      setError("Isletme adi zorunludur.")
      return
    }
    if (!businessAddress.trim()) {
      setError("Isletme adresi zorunludur.")
      return
    }
    if (!workStart || !workEnd) {
      setError("Baslangic ve bitis saatleri zorunludur.")
      return
    }

    setIsLoading(true)
    setError("")
    setSuccess("")
    try {
      const profile = await apiFetch<AdminProfile>("/api/v1/admin/profile", {
        method: "PATCH",
        body: JSON.stringify({
          business_name: businessName,
          business_address: businessAddress,
        }),
      })
      setBusinessName(profile.business_name ?? "")
      setBusinessAddress(profile.business_address ?? "")
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

  async function handleSavePersonalSettings() {
    if (!firstName.trim() || !lastName.trim()) {
      setError("Ad ve soyad zorunludur.")
      return
    }

    setProfileLoading(true)
    setError("")
    setSuccess("")
    try {
      const profile = await apiFetch<AdminProfile>("/api/v1/admin/profile", {
        method: "PATCH",
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
        }),
      })
      setFirstName(profile.first_name ?? "")
      setLastName(profile.last_name ?? "")
      setBusinessName(profile.business_name ?? "")
      setBusinessAddress(profile.business_address ?? "")
      setAdminPhone(profile.phone ?? "")
      setAdminEmail(profile.email ?? "")
      setSuccess("Kisisel ayarlar kaydedildi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kisisel ayarlar kaydedilemedi.")
    } finally {
      setProfileLoading(false)
    }
  }

  async function handleSaveSpecialDay() {
    if (!specialDate) {
      setError("Ozel gun tarihi secin.")
      return
    }
    if (!specialWorkStart || !specialWorkEnd) {
      setError("Acik ozel gun icin baslangic ve bitis saatleri zorunludur.")
      return
    }

    setSpecialLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiPut("/api/v1/admin/schedule/override", {
        date: specialDate,
        is_closed: false,
        work_start_time: specialWorkStart,
        work_end_time: specialWorkEnd,
        slot_duration_minutes: specialSlotDuration,
      })
      setSpecialExists(true)
      setSuccess("Ozel gun kaydedildi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Ozel gun kaydedilemedi.")
    } finally {
      setSpecialLoading(false)
    }
  }

  async function handleCloseDay() {
    if (!closeDate) {
      setError("Gun kapatma tarihi secin.")
      return
    }

    setCloseLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiPut("/api/v1/admin/schedule/override", {
        date: closeDate,
        is_closed: true,
        work_start_time: null,
        work_end_time: null,
        slot_duration_minutes: null,
      })
      setCloseExists(true)
      setSuccess("Gun kapatildi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gun kapatilamadi.")
    } finally {
      setCloseLoading(false)
    }
  }

  async function handleOpenClosedDay() {
    if (!closeDate) return

    setCloseLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiDelete(`/api/v1/admin/schedule/override?date=${closeDate}`)
      setCloseExists(false)
      setSuccess("Gun kapatma kaldirildi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Gun kapatma kaldirilamadi.")
    } finally {
      setCloseLoading(false)
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
            type="button"
            aria-label="Menüye dön"
            onClick={() => router.push("/admin/menu")}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-950 text-xl leading-none text-zinc-200 hover:border-zinc-600 hover:bg-zinc-800"
          >
            ←
          </button>
          <h1 className="text-lg font-bold text-zinc-100">
            {activeSection ? SETTINGS_SECTION_LABELS[activeSection] : "Ayarlar"}
          </h1>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4 max-w-sm mx-auto">
        <button
          type="button"
          onClick={() => router.push(SETTINGS_SECTION_PATHS.business)}
          className={`${activeSection ? "hidden" : "flex"} w-full items-center justify-between rounded-lg border px-4 py-3 text-left text-sm font-semibold transition-colors ${
            activeSection === "business"
              ? "border-zinc-500 bg-zinc-800 text-zinc-100"
              : "border-zinc-800 bg-zinc-900 text-zinc-300 hover:border-zinc-600"
          }`}
        >
          <span>İşletme Ayarları</span>
          <span aria-hidden="true">›</span>
        </button>

        {activeSection === "business" && (
          <>
            <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
              <h2 className="text-sm font-semibold text-zinc-200">Isletme Bilgileri</h2>
              <p className="text-xs text-zinc-400">Musterilerin iletisim alaninda gorecegi isletme adi ve adresi.</p>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Isletme Adi</label>
                <input
                  type="text"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900 text-zinc-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Adres</label>
                <textarea
                  value={businessAddress}
                  onChange={(e) => setBusinessAddress(e.target.value)}
                  rows={3}
                  className="block w-full max-w-full min-w-0 resize-none appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900 text-zinc-100"
                />
              </div>
            </div>

            <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3 overflow-hidden">
              <h2 className="text-sm font-semibold text-zinc-200">Calisma Saatleri</h2>
              <p className="text-xs text-zinc-400">Randevu alinabilecek gunluk baslangic ve bitis saatlerini belirler.</p>
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
              <p className="text-xs text-zinc-400">Her randevu slotunun kac dakika surecegini belirler.</p>
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
              <p className="text-xs text-zinc-400">Musterilerin kac gun sonrasina kadar randevu alabilecegini belirler.</p>
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
              <p className="text-xs text-zinc-400">Secili tarihte calisma saati ve slot suresi ayri yonetilir.</p>
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
              <h2 className="text-sm font-semibold text-zinc-200">Gun Kapatma</h2>
              <p className="text-xs text-zinc-400">Secili tarihi tamamen kapatir; istenirse tekrar acilir.</p>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Tarih</label>
                <input
                  type="date"
                  value={closeDate}
                  min={todayIso}
                  max={maxSpecialDate}
                  onChange={(e) => setCloseDate(e.target.value)}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={handleCloseDay}
                  disabled={closeLoading}
                  className="w-full py-2.5 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
                >
                  {closeLoading ? "Kaydediliyor..." : "Gunu Kapat"}
                </button>
                <button
                  onClick={handleOpenClosedDay}
                  disabled={closeLoading || !closeExists}
                  className="w-full py-2.5 bg-zinc-800 text-zinc-200 rounded-lg font-medium text-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-zinc-700 transition-colors"
                >
                  Kapatmayi Kaldir
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

            <button
              onClick={handleSaveSettings}
              disabled={isLoading}
              className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              {isLoading ? "Kaydediliyor..." : "Isletme Ayarlarini Kaydet"}
            </button>
          </>
        )}

        <button
          type="button"
          onClick={() => router.push(SETTINGS_SECTION_PATHS.personal)}
          className={`${activeSection ? "hidden" : "flex"} w-full items-center justify-between rounded-lg border px-4 py-3 text-left text-sm font-semibold transition-colors ${
            activeSection === "personal"
              ? "border-zinc-500 bg-zinc-800 text-zinc-100"
              : "border-zinc-800 bg-zinc-900 text-zinc-300 hover:border-zinc-600"
          }`}
        >
          <span>Kişisel Ayarlar</span>
          <span aria-hidden="true">›</span>
        </button>

        {activeSection === "personal" && (
          <>
            <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
              <h2 className="text-sm font-semibold text-zinc-200">Kisisel Bilgiler</h2>
              <p className="text-xs text-zinc-400">Ad ve soyad musterilere gorunen berber adi olarak kullanilir.</p>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Ad</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900 text-zinc-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Soyad</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent bg-zinc-900 text-zinc-100"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Numara</label>
                <input
                  type="text"
                  value={adminPhone}
                  readOnly
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-800 rounded-lg text-base outline-none bg-zinc-950 text-zinc-400"
                />
                <p className="mt-1 text-xs text-amber-300">Numaranızı değiştirmek için yetkiliyle iletişime geçin.</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">E-posta</label>
                <input
                  type="email"
                  value={adminEmail}
                  readOnly
                  className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-800 rounded-lg text-base outline-none bg-zinc-950 text-zinc-400"
                />
              </div>
            </div>

            <button
              onClick={handleSavePersonalSettings}
              disabled={profileLoading}
              className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              {profileLoading ? "Kaydediliyor..." : "Kisisel Ayarlari Kaydet"}
            </button>
          </>
        )}

        <button
          type="button"
          onClick={() => router.push(SETTINGS_SECTION_PATHS.whatsapp)}
          className={`${activeSection ? "hidden" : "flex"} w-full items-center justify-between rounded-lg border px-4 py-3 text-left text-sm font-semibold transition-colors ${
            activeSection === "whatsapp"
              ? "border-zinc-500 bg-zinc-800 text-zinc-100"
              : "border-zinc-800 bg-zinc-900 text-zinc-300 hover:border-zinc-600"
          }`}
        >
          <span>Whatsapp Bot Ayarları</span>
          <span aria-hidden="true">›</span>
        </button>

        {activeSection === "whatsapp" && (
          <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-2">
            <h2 className="text-sm font-semibold text-zinc-200">Whatsapp Bot Ayarları</h2>
            <p className="text-xs text-zinc-400">Bu alana Whatsapp bot ozellikleri eklenecek.</p>
          </div>
        )}

        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}
        {success && (
          <div className="text-sm text-emerald-300 bg-emerald-500/10 rounded-lg px-3 py-2">
            {success}
          </div>
        )}
      </div>
    </div>
  )
}
