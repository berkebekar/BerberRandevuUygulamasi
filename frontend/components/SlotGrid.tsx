/**
 * components/SlotGrid.tsx — Randevu slotlarını grid halinde gösteren bileşen.
 *
 * Backend'den gelen slot listesini renklendirilmiş butonlar olarak gösterir.
 * Slot durumlarına göre renk ve tıklanabilirlik:
 *   available  → yeşil, tıklanabilir
 *   booked     → gri, tıklanamaz ("Dolu" yazısı)
 *   blocked    → turuncu, tıklanamaz ("Kapalı" yazısı)
 *   past       → soluk gri, tıklanamaz ("Geçti" yazısı)
 */

"use client"

export type SlotStatus = "available" | "booked" | "blocked" | "past"

export interface Slot {
  slot_time: string   // ISO 8601 format: "2026-02-25T09:00:00+03:00"
  slot_end_time?: string
  status: SlotStatus
}

interface SlotGridProps {
  slots: Slot[]
  selectedSlot: string | null
  onSelect: (slotTime: string) => void
  isLoading?: boolean
}

/**
 * Slot zamanını "09:00" formatında gösterir.
 * slot_time UTC+3 olarak gelir, sadece saat:dakika kısmı alınır.
 */
function formatTime(slotTime: string): string {
  const date = new Date(slotTime)
  // toLocaleTimeString ile Türkiye saatini göster
  return date.toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  })
}

function formatSlotRange(slotStartTime: string, slotEndTime?: string): string {
  const start = formatTime(slotStartTime)
  if (!slotEndTime) return start
  return `${start}-${formatTime(slotEndTime)}`
}

/**
 * Slot durumuna göre Tailwind CSS sınıflarını döner.
 */
function slotClasses(status: SlotStatus, isSelected: boolean): string {
  const base = "w-full py-3 rounded-lg text-sm font-medium transition-colors border"

  if (isSelected) {
    // Seçili slot: koyu slate rengi
    return `${base} bg-zinc-100 text-zinc-950 border-zinc-100`
  }

  switch (status) {
    case "available":
      // Boş slot: yeşil, tıklanabilir
      return `${base} bg-emerald-500/10 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/20 cursor-pointer`
    case "booked":
      // Dolu slot: gri, tıklanamaz
      return `${base} bg-zinc-800 text-zinc-500 border-zinc-800 cursor-not-allowed`
    case "blocked":
      // Bloklu slot: turuncu, tıklanamaz
      return `${base} bg-zinc-800 text-zinc-200 border-zinc-700 cursor-not-allowed`
    case "past":
      // Geçmiş slot: soluk, tıklanamaz
      return `${base} bg-zinc-950 text-zinc-600 border-zinc-800/60 cursor-not-allowed`
    default:
      return `${base} bg-zinc-950 text-zinc-500 cursor-not-allowed`
  }
}

/**
 * Slot durumuna göre alt etiket metni döner.
 */
function slotLabel(status: SlotStatus): string | null {
  switch (status) {
    case "booked": return "Dolu"
    case "blocked": return "Kapalı"
    case "past": return "Geçti"
    default: return null
  }
}

export default function SlotGrid({ slots, selectedSlot, onSelect, isLoading }: SlotGridProps) {
  // Yükleniyor durumunda iskelet (skeleton) göster
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-2">
        {Array(9).fill(0).map((_, i) => (
          <div key={i} className="h-12 rounded-lg bg-zinc-800 animate-pulse" />
        ))}
      </div>
    )
  }

  // Hiç slot yoksa bilgilendirici mesaj göster
  if (slots.length === 0) {
    return (
      <div className="text-center py-8 text-zinc-400 text-sm">
        Bu gün için uygun randevu saati bulunmuyor.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {slots.map((slot) => {
        const isSelected = selectedSlot === slot.slot_time
        const label = slotLabel(slot.status)

        return (
          <button
            key={slot.slot_time}
            disabled={slot.status !== "available"}
            onClick={() => slot.status === "available" && onSelect(slot.slot_time)}
            className={slotClasses(slot.status, isSelected)}
          >
            {/* Saat gösterimi */}
            <div>{formatSlotRange(slot.slot_time, slot.slot_end_time)}</div>
            {/* Durum etiketi (Dolu, Kapalı, Geçti) */}
            {label && (
              <div className="text-xs mt-0.5 opacity-70">{label}</div>
            )}
          </button>
        )
      })}
    </div>
  )
}


