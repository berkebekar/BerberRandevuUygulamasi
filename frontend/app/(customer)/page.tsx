"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { SlotGrid } from "@/components"
import type { Slot } from "@/components"
import { apiFetch } from "@/lib/api"

type UserMe = {
  id: string
  first_name: string
  last_name: string
  phone: string
}

type MyBooking = {
  id: string
  slot_time: string
  status: "confirmed" | "cancelled"
}

function getWeekDays(): { date: string; label: string; shortDate: string }[] {
  const days = []
  const now = new Date()

  for (let i = 0; i < 7; i++) {
    const d = new Date(now)
    d.setDate(now.getDate() + i)

    const dateStr = d.toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })

    let label: string
    if (i === 0) label = "Bugun"
    else if (i === 1) label = "Yarin"
    else label = d.toLocaleDateString("tr-TR", { weekday: "short", timeZone: "Europe/Istanbul" })

    const shortDate = d.toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "short",
      timeZone: "Europe/Istanbul",
    })

    days.push({ date: dateStr, label, shortDate })
  }

  return days
}

function formatUpcomingBooking(slotTime: string): string {
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
  return `${dateText} ${timeText}`
}

export default function HomePage() {
  const router = useRouter()
  const weekDays = getWeekDays()

  const [selectedDate, setSelectedDate] = useState(weekDays[0].date)
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null)

  const [slots, setSlots] = useState<Slot[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const [profile, setProfile] = useState<UserMe | null>(null)
  const [bookingInfo, setBookingInfo] = useState("Randevu durumu yukleniyor...")

  const fetchSlots = useCallback(async (date: string) => {
    setIsLoading(true)
    setError("")
    setSelectedSlot(null)

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
      setIsLoading(false)
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
      const nearestUpcoming = (myBookings ?? [])
        .filter((b) => b.status === "confirmed")
        .filter((b) => new Date(b.slot_time) >= now)
        .sort((a, b) => new Date(a.slot_time).getTime() - new Date(b.slot_time).getTime())[0]

      if (!nearestUpcoming) {
        setBookingInfo("Mevcut randevunuz yok")
        return
      }

      setBookingInfo(formatUpcomingBooking(nearestUpcoming.slot_time))
    } catch {
      setProfile(null)
      setBookingInfo("Mevcut randevu bilgisi alinamadi")
    }
  }, [])

  useEffect(() => {
    fetchSlots(selectedDate)
  }, [selectedDate, fetchSlots])

  useEffect(() => {
    fetchProfileAndCurrentBooking()
  }, [fetchProfileAndCurrentBooking])

  function handleSlotSelect(slotTime: string) {
    setSelectedSlot(slotTime)
    sessionStorage.setItem("pendingSlot", slotTime)
    sessionStorage.setItem("pendingDate", selectedDate)
    router.push("/confirm")
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
          <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide mb-1">Mevcut Randevunuz</p>
          <p className="text-sm font-medium text-zinc-100">{bookingInfo}</p>
        </div>

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

          {error && (
            <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2 mb-3">
              {error}
            </div>
          )}

          <SlotGrid
            slots={slots}
            selectedSlot={selectedSlot}
            onSelect={handleSlotSelect}
            isLoading={isLoading}
          />
        </div>
      </div>
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


