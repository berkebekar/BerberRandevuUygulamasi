/**
 * components/BookingCard.tsx — Randevu özet kartı.
 *
 * Onay ekranında seçilen randevu bilgilerini gösterir.
 * Berber adı, tarih ve saat bilgisini düzenli gösterir.
 */

interface BookingCardProps {
  slotTime: string   // ISO 8601 format: "2026-02-25T09:00:00+03:00"
  barberName?: string
}

/**
 * ISO tarih stringini "Pazartesi, 25 �?ubat 2026" formatına çevirir.
 */
function formatDate(slotTime: string): string {
  return new Date(slotTime).toLocaleDateString("tr-TR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "Europe/Istanbul",
  })
}

/**
 * ISO tarih stringinden sadece saati "09:00" formatında alır.
 */
function formatTime(slotTime: string): string {
  return new Date(slotTime).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  })
}

export default function BookingCard({ slotTime, barberName }: BookingCardProps) {
  return (
    <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-5 shadow-sm">
      {/* Randevu başlığı */}
      <div className="flex items-center gap-3 mb-4">
        {/* Takvim ikonu yerine emoji — SVG kurmadan sade görünüm */}
        <div className="w-10 h-10 bg-zinc-800 rounded-lg flex items-center justify-center text-xl">
          ✂️
        </div>
        <div>
          <p className="text-xs text-zinc-400 uppercase tracking-wide">Randevu</p>
          <p className="font-semibold text-zinc-100">{barberName ?? "Berber"}</p>
        </div>
      </div>

      {/* Tarih ve saat bilgisi */}
      <div className="space-y-2 border-t border-zinc-800/60 pt-4">
        <div className="flex justify-between text-sm">
          <span className="text-zinc-400">Tarih</span>
          <span className="font-medium text-zinc-100 capitalize">{formatDate(slotTime)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-zinc-400">Saat</span>
          <span className="font-medium text-zinc-100">{formatTime(slotTime)}</span>
        </div>
      </div>
    </div>
  )
}


