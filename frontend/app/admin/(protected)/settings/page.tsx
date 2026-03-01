/**
 * app/admin/(protected)/settings/page.tsx — Admin ayarlar sayfasi.
 *
 * Calisma saatleri ve slot suresi burada guncellenir.
 */

"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch, apiPut } from "@/lib/api"

type BarberSettings = {
  slot_duration_minutes: number
  work_start_time: string // "09:00:00" veya "09:00"
  work_end_time: string
}

export default function AdminSettingsPage() {
  const router = useRouter()

  // Form state
  const [slotDuration, setSlotDuration] = useState(30)
  const [workStart, setWorkStart] = useState("09:00")
  const [workEnd, setWorkEnd] = useState("19:00")

  // UI state
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  /**
   * Backend'den mevcut ayarlari cek.
   */
  useEffect(() => {
    async function loadSettings() {
      setError("")
      try {
        const data = await apiFetch<BarberSettings | null>("/api/v1/admin/schedule/settings")
        // Backend kayit dondurduyse formu doldur
        if (data) {
          // Time input "HH:MM" istedigi icin sadece saat:dakika al
          setSlotDuration(data.slot_duration_minutes)
          setWorkStart(data.work_start_time.slice(0, 5))
          setWorkEnd(data.work_end_time.slice(0, 5))
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Ayarlar yuklenemedi.")
      }
    }

    loadSettings()
  }, [])

  /**
   * Ayarlari kaydet.
   */
  async function handleSave() {
    // Saatler bos ise kaydetme
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
      })
      setSuccess("Ayarlar kaydedildi.")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kaydetme basarisiz.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      {/* Ust baslik */}
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/admin")}
            className="text-zinc-400 hover:text-zinc-300 text-sm"
          >
            ← Geri
          </button>
          <h1 className="text-lg font-bold text-zinc-100">Ayarlar</h1>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4 max-w-sm mx-auto">
        {/* Calisma saatleri */}
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Calisma Saatleri</h2>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              Baslangic
            </label>
            <input
              type="time"
              value={workStart}
              onChange={(e) => setWorkStart(e.target.value)}
              className="w-full px-3 py-2.5 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">
              Bitis
            </label>
            <input
              type="time"
              value={workEnd}
              onChange={(e) => setWorkEnd(e.target.value)}
              className="w-full px-3 py-2.5 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
            />
          </div>
        </div>

        {/* Slot suresi */}
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Slot Suresi</h2>
          <div className="space-y-2">
            {[30, 40, 60].map((value) => (
              <label key={value} className="flex items-center gap-2 text-sm text-zinc-300">
                <input
                  type="radio"
                  name="slot_duration"
                  value={value}
                  checked={slotDuration === value}
                  onChange={() => setSlotDuration(value)}
                  className="accent-zinc-100"
                />
                {value} dk
              </label>
            ))}
          </div>
        </div>

        {/* Hata / basari */}
        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        {success && (
          <div className="text-sm text-emerald-300 bg-emerald-500/10 rounded-lg px-3 py-2">
            {success}
          </div>
        )}

        {/* Kaydet */}
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
        >
          {isLoading ? "Kaydediliyor..." : "Kaydet"}
        </button>
      </div>
    </div>
  )
}



