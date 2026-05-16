"use client"

import { useRouter } from "next/navigation"
import { apiFetch } from "@/lib/api"

const ITEMS = [
  { label: "İletişim", href: "/contact" },
  { label: "Ayarlar", href: "/settings" },
]

export default function CustomerMenuPage() {
  const router = useRouter()

  async function handleLogout() {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" })
    } catch {
      // no-op
    } finally {
      router.push("/auth")
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 px-4 py-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Panele dön"
            onClick={() => router.push("/")}
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-950/70 px-3 text-sm font-medium text-zinc-200 transition-colors hover:border-zinc-600 hover:bg-zinc-800 hover:text-white"
          >
            <span className="text-lg leading-none" aria-hidden="true">←</span>
            <span>Panel</span>
          </button>
          <h1 className="text-lg font-bold text-zinc-100">Menü</h1>
        </div>
      </div>

      <div className="space-y-3 px-4 pt-5">
        {ITEMS.map((item) => (
          <button
            key={item.href}
            type="button"
            onClick={() => router.push(item.href)}
            className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-4 text-left text-sm font-semibold text-zinc-100 hover:border-zinc-600"
          >
            <span>{item.label}</span>
            <span className="text-zinc-500">›</span>
          </button>
        ))}
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-4 text-left text-sm font-semibold text-red-200 hover:border-red-400/60"
        >
          <span>Çıkış</span>
          <span className="text-red-300">›</span>
        </button>
      </div>
    </div>
  )
}
