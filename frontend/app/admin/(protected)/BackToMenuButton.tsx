"use client"

import { useRouter } from "next/navigation"

export function BackToMenuButton() {
  const router = useRouter()

  return (
    <button
      type="button"
      onClick={() => router.push("/admin/menu")}
      className="inline-flex h-9 items-center gap-1.5 rounded-full border border-zinc-800 bg-zinc-950/70 px-3 text-sm font-medium text-zinc-200 transition-colors hover:border-zinc-600 hover:bg-zinc-800 hover:text-white"
    >
      <span className="text-lg leading-none" aria-hidden="true">←</span>
      <span>Menü</span>
    </button>
  )
}
