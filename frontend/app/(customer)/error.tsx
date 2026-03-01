/**
 * app/(customer)/error.tsx — Müşteri sayfaları için global hata sınırı.
 *
 * Beklenmedik bir hata oluşursa Next.js bu sayfayı gösterir.
 * "use client" zorunlu — React hata sınırları client-side çalışır.
 */

"use client"

import { useEffect } from "react"

interface ErrorPageProps {
  error: Error & { digest?: string }
  reset: () => void
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  // Hata üretim loglarına yazılsın
  useEffect(() => {
    console.error("[CustomerError]", error)
  }, [error])

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col justify-center items-center px-4 text-center">
      <div className="text-4xl mb-4">⚠️</div>
      <h2 className="text-lg font-bold text-zinc-100 mb-2">Bir şeyler yanlış gitti</h2>
      <p className="text-sm text-zinc-400 mb-6">
        Beklenmedik bir hata oluştu. Lütfen tekrar deneyin.
      </p>
      <button
        onClick={reset}
        className="px-6 py-2.5 bg-zinc-100 text-zinc-950 rounded-lg text-sm font-medium hover:bg-white transition-colors"
      >
        Tekrar Dene
      </button>
    </div>
  )
}


