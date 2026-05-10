"use client"

import { useState, useEffect, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { ActionConfirmSheet, SlotGrid } from "@/components"
import type { Slot } from "@/components"
import { apiDelete, apiFetch, apiPut } from "@/lib/api"
import { buildBookingDays } from "@/lib/bookingWindow"

type UserMe = {
  id: string
  first_name: string
  last_name: string
  phone: string
}

type TenantContactInfo = {
  name: string
  phone: string | null
  address: string | null
}

type MyBooking = {
  id: string
  slot_time: string
  status: "confirmed" | "cancelled" | "no_show"
  cancelled_by?: "admin" | "user" | "rescheduled_by_user" | "rescheduled_by_admin" | null
}

type UpcomingBookingState = {
  status: "loading" | "loaded" | "error"
  items: MyBooking[]
}

function formatBookingRow(slotTime: string): { timeText: string; dateText: string } {
  const dt = new Date(slotTime)
  const dateText = dt.toLocaleDateString("tr-TR", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    timeZone: "Europe/Istanbul",
  })
  const timeText = dt.toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  })
  return { timeText, dateText }
}

function getCancellationText(cancelledBy?: "admin" | "user" | "rescheduled_by_user" | "rescheduled_by_admin" | null): string {
  if (cancelledBy === "admin") return "Berber tarafından iptal edildi."
  if (cancelledBy === "user") return "Tarafınızca iptal edildi."
  if (cancelledBy === "rescheduled_by_user") return "Randevu saatiniz tarafınızca değiştirildi."
  if (cancelledBy === "rescheduled_by_admin") return "Randevu saatiniz berber tarafından değiştirildi."
  return "İptal edildi."
}

export default function HomePage() {
  const router = useRouter()
  const [maxBookingDaysAhead, setMaxBookingDaysAhead] = useState(14)
  const weekDays = useMemo(() => buildBookingDays(maxBookingDaysAhead), [maxBookingDaysAhead])

  const [selectedDate, setSelectedDate] = useState(() => buildBookingDays(14)[0].date)
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)

  const [slots, setSlots] = useState<Slot[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const [profile, setProfile] = useState<UserMe | null>(null)
  const [tenantContact, setTenantContact] = useState<TenantContactInfo | null>(null)
  const [contactOpen, setContactOpen] = useState(false)
  const [upcomingBookings, setUpcomingBookings] = useState<UpcomingBookingState>({
    status: "loading",
    items: [],
  })
  const [pendingCancelBooking, setPendingCancelBooking] = useState<MyBooking | null>(null)
  const [cancelLoading, setCancelLoading] = useState(false)

  const [pendingRescheduleBooking, setPendingRescheduleBooking] = useState<MyBooking | null>(null)
  const [rescheduleStep, setRescheduleStep] = useState<"confirm" | "slot_select">("confirm")
  const [rescheduleSlots, setRescheduleSlots] = useState<Slot[]>([])
  const [selectedRescheduleSlot, setSelectedRescheduleSlot] = useState<string | null>(null)
  const [rescheduleLoading, setRescheduleLoading] = useState(false)

  const fetchSlots = useCallback(async (date: string, options?: { resetSelection?: boolean; silent?: boolean }) => {
    const resetSelection = options?.resetSelection ?? false
    const silent = options?.silent ?? false
    if (!silent) setIsLoading(true)
    setError("")
    if (resetSelection) setSelectedSlot(null)

    try {
      const data = await apiFetch<{
        max_booking_days_ahead?: number
        slots: { datetime: string; end_datetime?: string; status: Slot["status"] }[]
      }>(
        `/api/v1/slots?date=${date}`
      )
      setMaxBookingDaysAhead(data.max_booking_days_ahead ?? 14)
      const normalized = (data.slots ?? []).map((slot) => ({
        slot_time: slot.datetime,
        slot_end_time: slot.end_datetime,
        status: slot.status,
      }))
      setSlots(normalized)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Slotlar yuklenemedi.")
      setSlots([])
    } finally {
      if (!silent) setIsLoading(false)
    }
  }, [])

  const fetchProfileAndCurrentBooking = useCallback(async () => {
    try {
      const [me, myBookings] = await Promise.all([
        apiFetch<UserMe>("/api/v1/users/me"),
        apiFetch<MyBooking[]>("/api/v1/bookings/my"),
      ])
      setProfile(me)

      const now = new Date()
      const sortedUpcoming = (myBookings ?? [])
        .filter((b) => b.status === "confirmed" || b.status === "cancelled")
        .filter((b) => new Date(b.slot_time) >= now)
        .sort((a, b) => new Date(a.slot_time).getTime() - new Date(b.slot_time).getTime())

      setUpcomingBookings({
        status: "loaded",
        items: sortedUpcoming,
      })
    } catch {
      setProfile(null)
      setUpcomingBookings({ status: "error", items: [] })
    }
  }, [])

  useEffect(() => {
    if (weekDays.some((day) => day.date === selectedDate)) return
    if (weekDays[0]) {
      setSelectedDate(weekDays[0].date)
    }
  }, [weekDays, selectedDate])

  useEffect(() => {
    fetchSlots(selectedDate, { resetSelection: true })
  }, [selectedDate, fetchSlots])

  useEffect(() => {
    fetchProfileAndCurrentBooking()
  }, [fetchProfileAndCurrentBooking])

  useEffect(() => {
    async function fetchTenantContact() {
      try {
        const data = await apiFetch<TenantContactInfo>("/api/v1/tenant/info")
        setTenantContact(data)
      } catch {
        setTenantContact(null)
      }
    }

    fetchTenantContact()
  }, [])

  useEffect(() => {
    const refreshBookings = () => {
      if (document.hidden) return
      fetchProfileAndCurrentBooking()
    }

    const intervalId = window.setInterval(refreshBookings, 15000)
    const onVisibilityChange = () => {
      if (!document.hidden) {
        fetchProfileAndCurrentBooking()
      }
    }

    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => {
      window.clearInterval(intervalId)
      document.removeEventListener("visibilitychange", onVisibilityChange)
    }
  }, [fetchProfileAndCurrentBooking])

  useEffect(() => {
    const refreshSlots = () => {
      if (document.hidden) return
      fetchSlots(selectedDate, { silent: true, resetSelection: false })
    }

    const intervalId = window.setInterval(refreshSlots, 15000)
    const onVisibilityChange = () => {
      if (!document.hidden) {
        fetchSlots(selectedDate, { silent: true, resetSelection: false })
      }
    }

    document.addEventListener("visibilitychange", onVisibilityChange)
    return () => {
      window.clearInterval(intervalId)
      document.removeEventListener("visibilitychange", onVisibilityChange)
    }
  }, [selectedDate, fetchSlots])

  function handleSlotSelect(slotTime: string) {
    setSelectedSlot(slotTime)
    sessionStorage.setItem("pendingSlot", slotTime)
    sessionStorage.setItem("pendingDate", selectedDate)
    router.push("/confirm")
  }

  function isRescheduleEligible(booking: MyBooking): boolean {
    if (booking.status !== "confirmed") return false
    const bookingTime = new Date(booking.slot_time)
    const twoHoursFromNow = new Date(Date.now() + 2 * 60 * 60 * 1000)
    return bookingTime > twoHoursFromNow
  }

  async function handleRescheduleConfirm() {
    if (!pendingRescheduleBooking) return
    setRescheduleLoading(true)
    try {
      const bookingDate = new Date(pendingRescheduleBooking.slot_time).toLocaleDateString("sv-SE", {
        timeZone: "Europe/Istanbul",
      })
      const data = await apiFetch<{
        slots: { datetime: string; end_datetime?: string; status: Slot["status"] }[]
      }>(`/api/v1/slots?date=${bookingDate}`)
      const available = (data.slots ?? [])
        .filter((s) => s.status === "available" && s.datetime !== pendingRescheduleBooking.slot_time)
        .map((s) => ({ slot_time: s.datetime, slot_end_time: s.end_datetime, status: s.status }))
      setRescheduleSlots(available)
      setSelectedRescheduleSlot(null)
      setRescheduleStep("slot_select")
    } catch {
      setError("Musait saatler yuklenemedi.")
      setPendingRescheduleBooking(null)
    } finally {
      setRescheduleLoading(false)
    }
  }

  async function handleRescheduleSubmit() {
    if (!pendingRescheduleBooking || !selectedRescheduleSlot) return
    setRescheduleLoading(true)
    try {
      await apiPut(`/api/v1/bookings/${pendingRescheduleBooking.id}/reschedule`, {
        new_slot_time: selectedRescheduleSlot,
      })
      setPendingRescheduleBooking(null)
      setSelectedRescheduleSlot(null)
      await Promise.all([
        fetchProfileAndCurrentBooking(),
        fetchSlots(selectedDate, { silent: true, resetSelection: false }),
      ])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Randevu duzenlenemedi.")
      setPendingRescheduleBooking(null)
    } finally {
      setRescheduleLoading(false)
    }
  }

  function handleRescheduleClose() {
    setPendingRescheduleBooking(null)
    setSelectedRescheduleSlot(null)
    setRescheduleStep("confirm")
  }

  async function handleConfirmCancelBooking() {
    if (!pendingCancelBooking) return
    setCancelLoading(true)
    setError("")
    try {
      await apiDelete(`/api/v1/bookings/${pendingCancelBooking.id}`)
      setPendingCancelBooking(null)
      await Promise.all([
        fetchProfileAndCurrentBooking(),
        fetchSlots(selectedDate, { silent: true, resetSelection: false }),
      ])
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Randevu iptal edilemedi.")
    } finally {
      setCancelLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-100">
              {profile ? `Hoşgeldin ${profile.first_name} ${profile.last_name}` : "Hoşgeldin"}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setContactOpen(true)}
              className="text-sm text-zinc-400 hover:text-zinc-300"
            >
              İletişim
            </button>
            <SettingsButton />
            <LogoutButton />
          </div>
        </div>
      </div>

      <div className="px-4 pt-4 space-y-4">
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-zinc-200">Mevcut Randevunuz</h2>
          </div>

          {upcomingBookings.status === "loading" && (
            <p className="text-sm font-medium text-zinc-100">Randevu durumu yukleniyor...</p>
          )}
          {upcomingBookings.status === "error" && (
            <p className="text-sm font-medium text-zinc-100">Mevcut randevu bilgisi alinamadi</p>
          )}
          {upcomingBookings.status === "loaded" && upcomingBookings.items.length === 0 && (
            <p className="text-sm font-medium text-zinc-100">Mevcut randevunuz yok</p>
          )}
          {upcomingBookings.status === "loaded" && upcomingBookings.items.length > 0 && (
            <div className="space-y-3">
              {upcomingBookings.items.map((booking) => {
                const { timeText, dateText } = formatBookingRow(booking.slot_time)
                const fullName = profile ? `${profile.first_name} ${profile.last_name}` : "Musteri"
                const isCancelled = booking.status === "cancelled"
                return (
                  <div
                    key={booking.id}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 ${
                      isCancelled ? "bg-zinc-950 border-zinc-800" : "bg-zinc-900 border-zinc-700"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className={`text-sm font-semibold break-words ${isCancelled ? "text-zinc-300" : "text-zinc-100"}`}>
                        {timeText} - {fullName}
                      </p>
                      <p className="text-xs text-zinc-500 mt-0.5 break-words">{dateText}</p>
                      {isCancelled && (
                        <p className="text-xs text-zinc-500 mt-0.5 break-words">{getCancellationText(booking.cancelled_by)}</p>
                      )}
                    </div>
                    {!isCancelled ? (
                      <div className="flex flex-col items-end gap-1.5 shrink-0 ml-3">
                        {isRescheduleEligible(booking) && (
                          <button
                            type="button"
                            onClick={() => {
                              setPendingRescheduleBooking(booking)
                              setRescheduleStep("confirm")
                            }}
                            className="text-sm text-blue-400 hover:text-blue-300"
                          >
                            Düzenle
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setPendingCancelBooking(booking)}
                          className="text-sm text-red-300 hover:text-red-200"
                        >
                          Iptal Et
                        </button>
                      </div>
                    ) : (
                      <span className="text-sm text-zinc-600 shrink-0 ml-3">Iptal Edildi</span>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">Tarih Secin</p>
            <span className="text-sm text-zinc-500">↔</span>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-hide">
            {weekDays.map((day) => {
              const isSelected = day.date === selectedDate

              return (
                <button
                  key={day.date}
                  onClick={() => setSelectedDate(day.date)}
                  className={`
                    flex-none flex flex-col items-center px-3 py-2.5 rounded-xl border transition-colors min-w-[60px]
                    ${isSelected
                      ? "bg-zinc-100 text-zinc-950 border-zinc-100"
                      : "bg-zinc-900 text-zinc-300 border-zinc-800 hover:border-zinc-300"
                    }
                  `}
                >
                  <span className="text-xs font-medium">{day.label}</span>
                  <span className={`text-xs mt-0.5 ${isSelected ? "text-zinc-700" : "text-zinc-500"}`}>
                    {day.shortDate}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Musait Saatler</p>

          <SlotGrid
            slots={slots}
            selectedSlot={selectedSlot}
            onSelect={handleSlotSelect}
            isLoading={isLoading}
          />
        </div>
      </div>

      <ActionConfirmSheet
        open={Boolean(pendingCancelBooking)}
        title="Randevuyu Iptal Et"
        description={
          pendingCancelBooking
            ? `${formatBookingRow(pendingCancelBooking.slot_time).timeText} saatindeki ${profile ? `${profile.first_name} ${profile.last_name}` : "musteri"} randevusu iptal edilecek.`
            : ""
        }
        confirmText="Onayla"
        cancelText="Vazgec"
        isLoading={cancelLoading}
        onCancel={() => setPendingCancelBooking(null)}
        onConfirm={handleConfirmCancelBooking}
      />

      {/* Düzenle: Adım 1 — Onay */}
      <ActionConfirmSheet
        open={Boolean(pendingRescheduleBooking) && rescheduleStep === "confirm"}
        title="Randevu Saatini Degistir"
        description={
          pendingRescheduleBooking
            ? `${formatBookingRow(pendingRescheduleBooking.slot_time).dateText} tarihindeki ${formatBookingRow(pendingRescheduleBooking.slot_time).timeText} randevunuzu gun icinde baska bir saatle degistirmek ister misiniz?`
            : ""
        }
        confirmText="Evet, Devam Et"
        cancelText="Vazgec"
        confirmTone="neutral"
        isLoading={rescheduleLoading}
        onCancel={handleRescheduleClose}
        onConfirm={handleRescheduleConfirm}
      />

      {/* Düzenle: Adım 2 — Saat Seçimi */}
      <ActionConfirmSheet
        open={Boolean(pendingRescheduleBooking) && rescheduleStep === "slot_select"}
        title="Yeni Saat Secin"
        description={
          pendingRescheduleBooking
            ? `${formatBookingRow(pendingRescheduleBooking.slot_time).dateText} icin musait saatler:`
            : ""
        }
        confirmText="Onayla"
        cancelText="Vazgec"
        confirmTone="neutral"
        isLoading={rescheduleLoading}
        confirmDisabled={!selectedRescheduleSlot}
        onCancel={handleRescheduleClose}
        onConfirm={handleRescheduleSubmit}
      >
        {rescheduleSlots.length === 0 ? (
          <p className="text-sm text-zinc-500 text-center py-2">Bu gun icin musait saat bulunamadi.</p>
        ) : (
          <div className="grid grid-cols-3 gap-2 max-h-52 overflow-y-auto">
            {rescheduleSlots.map((slot) => {
              const timeLabel = new Date(slot.slot_time).toLocaleTimeString("tr-TR", {
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "Europe/Istanbul",
              })
              const isSelected = selectedRescheduleSlot === slot.slot_time
              return (
                <button
                  key={slot.slot_time}
                  type="button"
                  onClick={() => setSelectedRescheduleSlot(slot.slot_time)}
                  className={`py-2 rounded-lg text-sm font-medium border transition-colors ${
                    isSelected
                      ? "bg-zinc-100 text-zinc-900 border-zinc-100"
                      : "bg-zinc-800 text-zinc-200 border-zinc-700 hover:border-zinc-400"
                  }`}
                >
                  {timeLabel}
                </button>
              )
            })}
          </div>
        )}
      </ActionConfirmSheet>

      <ContactSheet
        open={contactOpen}
        contact={tenantContact}
        onClose={() => setContactOpen(false)}
      />
    </div>
  )
}

function ContactSheet({
  open,
  contact,
  onClose,
}: {
  open: boolean
  contact: TenantContactInfo | null
  onClose: () => void
}) {
  const [copiedField, setCopiedField] = useState<"phone" | "address" | null>(null)

  if (!open) return null

  async function copyValue(field: "phone" | "address", value?: string | null) {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopiedField(field)
      window.setTimeout(() => setCopiedField(null), 1800)
    } catch {
      setCopiedField(null)
    }
  }

  const phone = contact?.phone || "-"
  const address = contact?.address || "-"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Kapat"
        className="absolute inset-0 bg-black/70"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg rounded-lg border border-zinc-800 bg-zinc-900 p-4 shadow-2xl shadow-black/40">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-zinc-100">İletişim</h3>
          <button type="button" onClick={onClose} className="text-sm text-zinc-400 hover:text-zinc-200">
            Kapat
          </button>
        </div>
        <div className="mt-4 space-y-2">
          <button
            type="button"
            onClick={() => copyValue("phone", contact?.phone)}
            disabled={!contact?.phone}
            className="relative w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-3 pr-10 text-left text-sm text-zinc-200 disabled:cursor-default disabled:opacity-70"
          >
            <span className="absolute right-3 top-3 text-base" aria-hidden="true">
              📋
            </span>
            <span className="block text-xs text-zinc-500">Berber No</span>
            <span className="mt-1 block break-all font-medium">{phone}</span>
            {copiedField === "phone" && <span className="mt-1 block text-xs text-emerald-300">Kopyalandı!</span>}
          </button>
          <button
            type="button"
            onClick={() => copyValue("address", contact?.address)}
            disabled={!contact?.address}
            className="relative w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-3 pr-10 text-left text-sm text-zinc-200 disabled:cursor-default disabled:opacity-70"
          >
            <span className="absolute right-3 top-3 text-base" aria-hidden="true">
              📋
            </span>
            <span className="block text-xs text-zinc-500">Adres</span>
            <span className="mt-1 block break-words font-medium">{address}</span>
            {copiedField === "address" && <span className="mt-1 block text-xs text-emerald-300">Kopyalandı!</span>}
          </button>
        </div>
        <a
          href="https://bbsoft.com.tr"
          target="_blank"
          rel="noreferrer"
          className="mt-4 block text-center text-sm font-medium text-zinc-300 hover:text-white"
        >
          Bu hizmet için detaylı bilgi almak için web sitemizi ziyaret edin bbsoft.com.tr
        </a>
      </div>
    </div>
  )
}

function SettingsButton() {
  const router = useRouter()
  return (
    <button
      onClick={() => router.push("/settings")}
      className="text-sm text-zinc-400 hover:text-zinc-300"
    >
      Ayarlar
    </button>
  )
}

function LogoutButton() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)

  async function handleLogout() {
    setIsLoading(true)
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" })
    } catch {
      // no-op
    } finally {
      setIsLoading(false)
      router.push("/auth")
    }
  }

  return (
    <button
      onClick={handleLogout}
      disabled={isLoading}
      className="text-sm text-zinc-400 hover:text-zinc-300 disabled:opacity-50"
    >
      Cikis
    </button>
  )
}
