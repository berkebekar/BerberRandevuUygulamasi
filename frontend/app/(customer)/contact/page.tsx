"use client"

import { useEffect, useState } from "react"
import { TenantUnavailable } from "@/components"
import { apiFetch, isTenantAccessError } from "@/lib/api"
import { BackToCustomerMenuButton } from "../BackToCustomerMenuButton"

type TenantContactInfo = {
  name: string
  phone: string | null
  address: string | null
}

export default function CustomerContactPage() {
  const [contact, setContact] = useState<TenantContactInfo | null>(null)
  const [copiedField, setCopiedField] = useState<"phone" | "address" | null>(null)
  const [error, setError] = useState("")
  const [tenantError, setTenantError] = useState("")

  useEffect(() => {
    async function loadContact() {
      try {
        const data = await apiFetch<TenantContactInfo>("/api/v1/tenant/info")
        setContact(data)
      } catch (err: unknown) {
        if (isTenantAccessError(err)) {
          setTenantError(err.message)
          return
        }
        setError(err instanceof Error ? err.message : "Iletisim bilgileri yuklenemedi.")
      }
    }
    loadContact()
  }, [])

  async function copyValue(field: "phone" | "address", value?: string | null) {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopiedField(field)
      window.setTimeout(() => setCopiedField(null), 1800)
    } catch {
      setCopiedField(null)
    }
  }

  if (tenantError) {
    return <TenantUnavailable message={tenantError} />
  }

  const phone = contact?.phone || "-"
  const address = contact?.address || "-"

  return (
    <div className="min-h-screen bg-zinc-950 pb-8">
      <div className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900 px-4 py-4">
        <div className="flex items-center gap-3">
          <BackToCustomerMenuButton />
          <h1 className="text-lg font-bold text-zinc-100">İletişim</h1>
        </div>
      </div>

      <div className="space-y-4 px-4 pt-5">
        {error && <div className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}
        <section className="space-y-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <div>
            <p className="text-xs text-zinc-500">Salon</p>
            <p className="mt-1 text-sm font-semibold text-zinc-100">{contact?.name || "-"}</p>
          </div>
          <button
            type="button"
            onClick={() => copyValue("phone", contact?.phone)}
            disabled={!contact?.phone}
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-3 text-left text-sm text-zinc-200 disabled:cursor-default disabled:opacity-70"
          >
            <span className="min-w-0">
              <span className="block text-xs text-zinc-500">Berber No</span>
              <span className="mt-1 block break-all font-medium">{phone}</span>
              {copiedField === "phone" && <span className="mt-1 block text-xs text-emerald-300">Kopyalandı</span>}
            </span>
            <span className="shrink-0 text-xs font-semibold text-zinc-400">Kopyala</span>
          </button>
          <button
            type="button"
            onClick={() => copyValue("address", contact?.address)}
            disabled={!contact?.address}
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-3 text-left text-sm text-zinc-200 disabled:cursor-default disabled:opacity-70"
          >
            <span className="min-w-0">
              <span className="block text-xs text-zinc-500">Adres</span>
              <span className="mt-1 block break-words font-medium">{address}</span>
              {copiedField === "address" && <span className="mt-1 block text-xs text-emerald-300">Kopyalandı</span>}
            </span>
            <span className="shrink-0 text-xs font-semibold text-zinc-400">Kopyala</span>
          </button>
        </section>
        <a
          href="https://bbsoft.com.tr"
          target="_blank"
          rel="noreferrer"
          className="block text-center text-sm font-medium text-zinc-300 hover:text-white"
        >
          Bu hizmet için detaylı bilgi almak için web sitemizi ziyaret edin bbsoft.com.tr
        </a>
      </div>
    </div>
  )
}
