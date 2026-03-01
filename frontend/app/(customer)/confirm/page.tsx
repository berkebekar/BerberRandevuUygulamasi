/**
 * app/(customer)/confirm/page.tsx — Randevu onay sayfası.
 *
 * Ana sayfada seçilen slot bilgisi sessionStorage'dan okunur.
 * Kullanıcıya özet gösterilir: tarih, saat.
 * "Onayla" butonuna basılınca POST /api/v1/bookings çağrılır.
 * Başarıyla randevu oluşturulunca başarı ekranı gösterilir.
 */

"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { BookingCard } from "@/components"
import { apiPost } from "@/lib/api"

export default function ConfirmPage() {
  const router = useRouter()

  // sessionStorage'dan seçilen slot bilgisini al
  const [slotTime, setSlotTime] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  // Randevu başarıyla oluşturulduysa true
  const [isSuccess, setIsSuccess] = useState(false)

  // Sayfa ilk render'da sessionStorage oku
  // useEffect kullanıyoruz çünkü sessionStorage sunucu tarafında yoktur (SSR)
  useEffect(() => {
    const stored = sessionStorage.getItem("pendingSlot")
    if (!stored) {
      // Slot seçilmeden bu sayfaya gelinirse ana sayfaya gönder
      router.replace("/")
      return
    }
    setSlotTime(stored)
  }, [router])

  /**
   * Randevu oluşturma isteği gönderir.
   * SELECT FOR UPDATE ile atomik işlem backend'de yapılır.
   */
  async function handleConfirm() {
    if (!slotTime) return

    setError("")
    setIsLoading(true)

    try {
      await apiPost("/api/v1/bookings", { slot_time: slotTime })

      // Başarılı: sessionStorage'ı temizle, başarı ekranını göster
      sessionStorage.removeItem("pendingSlot")
      sessionStorage.removeItem("pendingDate")
      setIsSuccess(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Randevu oluşturulamadı.")
    } finally {
      setIsLoading(false)
    }
  }

  // Slot bilgisi yüklenene kadar boş ekran göster
  if (!slotTime) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Yükleniyor...</div>
      </div>
    )
  }

  // ── Başarı ekranı ──
  if (isSuccess) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col justify-center px-4">
        <div className="w-full max-w-sm mx-auto text-center">
          {/* Başarı ikonu */}
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg
              className="h-8 w-8 text-green-800"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10zm-1.667-5.333L7 12.666l1.333-1.333 2 2 5.333-5.333L17 9l-6.667 7.667z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-zinc-100 mb-2">Randevunuz Alındı!</h2>
          <p className="text-sm text-zinc-400 mb-6">
            Randevunuz başarıyla oluşturuldu.
          </p>

          {/* Randevu özet kartı */}
          <div className="mb-6">
            <BookingCard slotTime={slotTime} />
          </div>

          {/* Ana sayfaya dön */}
          <button
            onClick={() => router.push("/")}
            className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm hover:bg-white transition-colors"
          >
            Ana Sayfaya Dön
          </button>
        </div>
      </div>
    )
  }

  // ── Onay ekranı ──
  return (
    <div className="min-h-screen bg-zinc-950 pb-8">

      {/* Üst başlık */}
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="text-zinc-400 hover:text-zinc-300 text-sm"
          >
            ← Geri
          </button>
          <h1 className="text-lg font-bold text-zinc-100">Randevu Onayı</h1>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4 max-w-sm mx-auto">

        {/* Randevu özet kartı */}
        <BookingCard slotTime={slotTime} />

        {/* Bilgi notu */}
        <div className="bg-sky-500/10 border border-sky-500/30 rounded-lg px-3 py-2.5">
          <p className="text-sm text-sky-300">
            Randevunuzu onayladıktan sonra iptal için berberinizle iletişime geçin.
          </p>
        </div>

        {/* Hata mesajı */}
        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2.5">
            {error}
          </div>
        )}

        {/* Onayla butonu */}
        <button
          onClick={handleConfirm}
          disabled={isLoading}
          className="w-full py-3.5 bg-zinc-100 text-zinc-950 rounded-xl font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
        >
          {isLoading ? "Randevu Oluşturuluyor..." : "Randevuyu Onayla"}
        </button>

        {/* İptal butonu */}
        <button
          onClick={() => router.back()}
          disabled={isLoading}
          className="w-full py-3 text-zinc-400 text-sm hover:text-zinc-300 disabled:opacity-50"
        >
          Vazgeç, Farklı Saat Seç
        </button>

      </div>
    </div>
  )
}


