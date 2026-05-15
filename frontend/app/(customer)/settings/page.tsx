"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { TenantUnavailable } from "@/components"
import { apiFetch, isTenantAccessError } from "@/lib/api"

type UserMe = {
  first_name: string
  last_name: string
}

export default function CustomerSettingsPage() {
  const router = useRouter()
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [tenantError, setTenantError] = useState("")
  const [success, setSuccess] = useState("")

  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await apiFetch<UserMe>("/api/v1/users/me")
        setFirstName(data.first_name)
        setLastName(data.last_name)
      } catch (err: unknown) {
        if (isTenantAccessError(err)) {
          setTenantError(err.message)
          return
        }
        setError(err instanceof Error ? err.message : "Profil yuklenemedi.")
      }
    }
    loadProfile()
  }, [])

  async function handleSave() {
    const trimmedFirst = firstName.trim()
    const trimmedLast = lastName.trim()
    if (trimmedFirst.length < 2 || trimmedLast.length < 2) {
      setError("Ad ve soyad en az 2 karakter olmalidir.")
      return
    }
    setIsLoading(true)
    setError("")
    setSuccess("")
    try {
      await apiFetch("/api/v1/users/me", {
        method: "PATCH",
        body: JSON.stringify({ first_name: trimmedFirst, last_name: trimmedLast }),
      })
      setSuccess("Bilgiler guncellendi.")
    } catch (err: unknown) {
      if (isTenantAccessError(err)) {
        setTenantError(err.message)
        return
      }
      setError(err instanceof Error ? err.message : "Kaydetme basarisiz.")
    } finally {
      setIsLoading(false)
    }
  }

  if (tenantError) {
    return <TenantUnavailable message={tenantError} />
  }

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="text-zinc-400 hover:text-zinc-300 text-sm"
          >
            {"<- Geri"}
          </button>
          <h1 className="text-lg font-bold text-zinc-100">Ayarlar</h1>
        </div>
      </div>

      <div className="px-4 pt-6 space-y-4 max-w-sm mx-auto">
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-200">Kisisel Bilgiler</h2>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Ad</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base text-zinc-100 bg-zinc-950 outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1">Soyad</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="block w-full max-w-full min-w-0 appearance-none px-3 py-2.5 border border-zinc-700 rounded-lg text-base text-zinc-100 bg-zinc-950 outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
            />
          </div>
        </div>

        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</div>
        )}
        {success && (
          <div className="text-sm text-emerald-300 bg-emerald-500/10 rounded-lg px-3 py-2">
            {success}
          </div>
        )}

        <button
          onClick={handleSave}
          disabled={isLoading}
          className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
        >
          {isLoading ? "Kaydediliyor..." : "Kaydet"}
        </button>
      </div>
    </div>
  )
}
