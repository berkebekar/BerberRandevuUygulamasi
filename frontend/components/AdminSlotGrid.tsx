/**
 * components/AdminSlotGrid.tsx — Admin icin slot grid bileşeni.
 *
 * Bu grid, adminin slotlari kapatmasi ve bloklu slotlari acmasi icin kullanilir.
 * Müşteri gridinden farki: available ve blocked durumlarinda aksiyon vardir.
 */

"use client"

export type AdminSlotStatus = "available" | "booked" | "blocked" | "past"

export interface AdminSlotItem {
  datetime: string // ISO 8601 format: "2026-02-25T09:00:00+03:00"
  end_datetime?: string
  status: AdminSlotStatus
  block_id?: string | null // blocked ise, acma icin gerekli blok id
}

interface AdminSlotGridProps {
  slots: AdminSlotItem[]
  isLoading?: boolean
  onBlock: (slotDatetime: string) => void
  onUnblock: (blockId: string) => void
}

/**
 * Slot durumuna gore Tailwind siniflarini dondurur.
 */
function slotClasses(status: AdminSlotStatus): string {
  const base = "w-full py-3 rounded-lg text-sm font-medium transition-colors border"

  switch (status) {
    case "available":
      // Bos slot: admin kapatabilir
      return `${base} bg-emerald-500/10 text-emerald-300 border-emerald-500/40 hover:bg-emerald-500/20 cursor-pointer`
    case "booked":
      // Dolu slot: admin iptal etmeden kapatamaz
      return `${base} bg-zinc-800 text-zinc-500 border-zinc-800 cursor-not-allowed`
    case "blocked":
      // Bloklu slot: admin acabilir
      return `${base} bg-zinc-800 text-zinc-200 border-zinc-700 hover:bg-zinc-700 cursor-pointer`
    case "past":
      // Gecmis slot: degisiklik yok
      return `${base} bg-zinc-950 text-zinc-600 border-zinc-800/60 cursor-not-allowed`
    default:
      return `${base} bg-zinc-950 text-zinc-500 cursor-not-allowed`
  }
}

/**
 * Slot durumuna gore alt etiket metnini dondurur.
 */
function slotLabel(status: AdminSlotStatus): string | null {
  switch (status) {
    case "booked":
      return "Dolu"
    case "blocked":
      return "Kapatildi"
    case "past":
      return "Gecti"
    default:
      return null
  }
}

function formatTime(dt: string): string {
  return new Date(dt).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  })
}

export default function AdminSlotGrid({
  slots,
  isLoading,
  onBlock,
  onUnblock,
}: AdminSlotGridProps) {
  // Yukleniyor durumunda iskelet goster
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-2">
        {Array(9).fill(0).map((_, i) => (
          <div key={i} className="h-12 rounded-lg bg-zinc-800 animate-pulse" />
        ))}
      </div>
    )
  }

  // Hic slot yoksa bilgilendir
  if (slots.length === 0) {
    return (
      <div className="text-center py-8 text-zinc-400 text-sm">
        Bu gun icin slot bulunamadi.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-2">
      {slots.map((slot) => {
        const label = slotLabel(slot.status)
        const isBlocked = slot.status === "blocked"
        const isAvailable = slot.status === "available"
        const canClick = isAvailable || (isBlocked && slot.block_id)

        return (
          <button
            key={slot.datetime}
            disabled={!canClick}
            onClick={() => {
              // Available: slotu kapat, Blocked: block_id varsa ac
              // Eger slot available ise kapatma aksiyonu calistir
              if (isAvailable) onBlock(slot.datetime)
              // Eger slot blocked ve block_id varsa acma aksiyonu calistir
              if (isBlocked && slot.block_id) onUnblock(slot.block_id)
            }}
            className={slotClasses(slot.status)}
          >
            {/* Saat gosterimi */}
            <div>{formatTime(slot.datetime)}</div>
            {/* Durum etiketi */}
            {label && (
              <div className="text-xs mt-0.5 opacity-70">{label}</div>
            )}
          </button>
        )
      })}
    </div>
  )
}


