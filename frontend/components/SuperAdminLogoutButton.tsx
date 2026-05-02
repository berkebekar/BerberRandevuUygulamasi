"use client"

import { useState } from "react"

import { superAdminPost } from "@/lib/superadmin-api"

export default function SuperAdminLogoutButton() {
  const [isLoading, setIsLoading] = useState(false)

  async function handleLogout() {
    setIsLoading(true)
    try {
      await superAdminPost("/api/v1/superadmin/auth/logout", {})
    } catch {
      // Session zaten yoksa da login ekranina yonlendir.
    } finally {
      window.location.assign("/superadmin/login")
    }
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={isLoading}
      className="rounded-lg border border-zinc-700 px-3 py-2 text-sm font-medium text-zinc-100 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {isLoading ? "Cikis..." : "Cikis"}
    </button>
  )
}
