"use client"

import { useRouter } from "next/navigation"

export function BackToCustomerMenuButton() {
  const router = useRouter()

  return (
    <button
      type="button"
      aria-label="Menüye dön"
      onClick={() => router.push("/menu")}
      className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-zinc-800 bg-zinc-950/70 text-lg leading-none text-zinc-200 transition-colors hover:border-zinc-600 hover:bg-zinc-800 hover:text-white"
    >
      ←
    </button>
  )
}
