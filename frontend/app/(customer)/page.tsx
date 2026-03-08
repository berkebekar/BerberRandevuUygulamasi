"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { ActionConfirmSheet, SlotGrid } from "@/components"
import type { Slot } from "@/components"
import { apiDelete, apiFetch } from "@/lib/api"
import { buildBookingDays } from "@/lib/bookingWindow"

type UserMe = {
  id: string
  first_name: string
  last_name: string
  phone: string
}

type MyBooking = {
  id: string
  slot_time: string
  status: "confirmed" | "cancelled" | "no_show"
  cancelled_by?: "admin" | "user" | null
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

function getCancellationText(cancelledBy?: "admin" | "user" | null): string {
  if (cancelledBy === "admin") return "Berber tarafından iptal edildi."
  if (cancelledBy === "user") return "Tarafınızca iptal edildi."
  return "İptal edildi."
}

export default function HomePage() {
  const router = useRouter()
  const weekDays = buildBookingDays()

  const [selectedDate, setSelectedDate] = useState(weekDays[0].date)
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)

  const [slots, setSlots] = useState<Slot[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const [profile, setProfile] = useState<UserMe | null>(null)
  const [upcomingBookings, setUpcomingBookings] = useState<UpcomingBookingState>({
    status: "loading",
    items: [],
  })
  const [pendingCancelBooking, setPendingCancelBooking] = useState<MyBooking | null>(null)
  const [cancelLoading, setCancelLoading] = useState(false)

  const fetchSlots = useCallback(async (date: string, options?: { resetSelection?: boolean; silent?: boolean }) => {
    const resetSelection = options?.resetSelection ?? false
    const silent = options?.silent ?? false
    if (!silent) setIsLoading(true)
    setError("")
    if (resetSelection) setSelectedSlot(null)

    try {
      const data = await apiFetch<{ slots: { datetime: string; end_datetime?: string; status: Slot["status"] }[] }>(
        `/api/v1/slots?date=${date}`
      )
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
    fetchSlots(selectedDate, { resetSelection: true })
  }, [selectedDate, fetchSlots])

  useEffect(() => {
    fetchProfileAndCurrentBooking()
  }, [fetchProfileAndCurrentBooking])

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
            <p className="text-xs text-zinc-400">Lütfen randevu almak için bir gün ve bir saat Seçin</p>
          </div>
          <LogoutButton />
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
                    <div>
                      <p className={`text-sm font-semibold ${isCancelled ? "text-zinc-300" : "text-zinc-100"}`}>
                        {timeText} - {fullName}
                      </p>
                      <p className="text-xs text-zinc-500 mt-0.5">{dateText}</p>
                      {isCancelled && (
                        <p className="text-xs text-zinc-500 mt-0.5">{getCancellationText(booking.cancelled_by)}</p>
                      )}
                    </div>
                    {!isCancelled ? (
                      <button
                        type="button"
                        onClick={() => setPendingCancelBooking(booking)}
                        className="text-sm text-red-300 hover:text-red-200"
                      >
                        Iptal Et
                      </button>
                    ) : (
                      <span className="text-sm text-zinc-600">Iptal Edildi</span>
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
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-2">Tarih Secin</p>
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
    </div>
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
