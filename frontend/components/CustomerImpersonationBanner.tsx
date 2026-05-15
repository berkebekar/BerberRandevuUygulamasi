"use client"

import { useState } from "react"

import { apiPost } from "@/lib/api"

function superAdminHomeUrl(): string {
  const configuredDomain = (process.env.NEXT_PUBLIC_APP_DOMAIN ?? "bbsoft.com.tr")
    .trim()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .split("/")[0]

  return `https://superadmin.${configuredDomain}`
}

export default function CustomerImpersonationBanner() {
  const [isExiting, setIsExiting] = useState(false)
  const [error, setError] = useState("")

  async function handleExit() {
    setIsExiting(true)
    setError("")
    try {
      await apiPost("/api/v1/superadmin/impersonate/exit", {})
      window.location.assign(superAdminHomeUrl())
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Super admin oturumuna donulemedi.")
      }
      setIsExiting(false)
    }
  }

  return (
    <div className="mx-auto mb-3 max-w-lg rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
      <p className="font-medium text-amber-200">Super Admin olarak kullanici panelini goruntuluyorsunuz.</p>
      <p className="mt-1 text-amber-100/90">Bu oturum impersonation modundadir.</p>
      {error && <p className="mt-2 text-red-300">{error}</p>}
      <button
        type="button"
        onClick={handleExit}
        disabled={isExiting}
        className="mt-3 rounded border border-amber-300/60 px-3 py-1.5 text-xs font-semibold text-amber-100 hover:bg-amber-400/10 disabled:opacity-60"
      >
        {isExiting ? "Donuluyor..." : "Super Admin'e Don"}
      </button>
    </div>
  )
}
