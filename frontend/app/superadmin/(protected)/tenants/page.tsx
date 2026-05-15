"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"

import { SuperAdminApiError, superAdminGet, superAdminPost } from "@/lib/superadmin-api"

import type { TenantDomainSyncResponse, TenantListResponse, TenantStatus } from "./types"
import { buildTenantAdminUrl, formatTenantDate, getTenantStatusBadgeClass, getTenantStatusLabel } from "./utils"

const SORTABLE_COLUMNS = ["created_at", "name", "subdomain", "user_count", "booking_count"] as const
type SortKey = (typeof SORTABLE_COLUMNS)[number]

function buildTenantListPath(params: {
  page: number
  status: TenantStatus | "all"
  dateFrom: string
  dateTo: string
  search: string
  sortBy: SortKey
  sortOrder: "asc" | "desc"
}) {
  const query = new URLSearchParams()
  query.set("page", String(params.page))
  query.set("page_size", "20")
  query.set("sort_by", params.sortBy)
  query.set("sort_order", params.sortOrder)
  if (params.status !== "all") query.set("status", params.status)
  if (params.dateFrom) query.set("date_from", params.dateFrom)
  if (params.dateTo) query.set("date_to", params.dateTo)
  if (params.search.trim()) query.set("search", params.search.trim())
  return `/api/v1/superadmin/tenants?${query.toString()}`
}

export default function SuperAdminTenantsPage() {
  const [listData, setListData] = useState<TenantListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [actionMessage, setActionMessage] = useState("")

  const [page, setPage] = useState(1)
  const [status, setStatus] = useState<TenantStatus | "all">("all")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const [sortBy, setSortBy] = useState<SortKey>("created_at")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [pendingImpersonateId, setPendingImpersonateId] = useState<string | null>(null)
  const [syncingDomains, setSyncingDomains] = useState(false)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setPage(1)
      setSearchTerm(searchInput)
    }, 400)
    return () => window.clearTimeout(timeoutId)
  }, [searchInput])

  useEffect(() => {
    let mounted = true

    async function fetchTenants() {
      setLoading(true)
      setError("")
      try {
        const data = await superAdminGet<TenantListResponse>(
          buildTenantListPath({ page, status, dateFrom, dateTo, search: searchTerm, sortBy, sortOrder })
        )
        if (!mounted) return
        setListData(data)
      } catch (err: unknown) {
        if (!mounted) return
        if (err instanceof SuperAdminApiError) {
          setError(err.message)
        } else if (err instanceof Error) {
          setError(err.message)
        } else {
          setError("Tenant listesi su an yuklenemiyor.")
        }
        setListData(null)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    fetchTenants()
    return () => {
      mounted = false
    }
  }, [page, status, dateFrom, dateTo, searchTerm, sortBy, sortOrder])

  const rows = listData?.items ?? []
  const pagination = listData?.pagination

  const pageInfo = useMemo(() => {
    if (!pagination) return ""
    return `${pagination.page}. sayfa / ${pagination.total_pages} - Toplam ${pagination.total} tenant`
  }, [pagination])

  function handleSort(column: SortKey) {
    setPage(1)
    if (sortBy !== column) {
      setSortBy(column)
      setSortOrder("asc")
      return
    }
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"))
  }

  async function handleImpersonate(tenantId: string, subdomain: string) {
    setPendingImpersonateId(tenantId)
    setError("")
    setActionMessage("")
    try {
      await superAdminPost("/api/v1/superadmin/tenants/" + tenantId + "/impersonate", {})
      const targetUrl = buildTenantAdminUrl(subdomain)
      window.open(targetUrl, "_blank", "noopener,noreferrer")
      setActionMessage("Impersonation baslatildi. Tenant admin paneli yeni sekmede acildi.")
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) {
        setError(err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Impersonation baslatilamadi.")
      }
    } finally {
      setPendingImpersonateId(null)
    }
  }

  function buildDomainSyncMessage(result: TenantDomainSyncResponse): string {
    if (result.reason === "wildcard_domain_strategy") {
      return "Wildcard domain stratejisi aktif. Tenant domainleri proxy tarafinda yakalanir; Coolify domain sync gerekmez."
    }
    if (!result.enabled) {
      return `Coolify otomasyonu kapali veya eksik ayar var: ${result.reason ?? "coolify_not_configured"}`
    }
    if (result.error) {
      return `Coolify domain sync basarisiz: ${result.error}`
    }
    const deployText = result.deploy_requested ? "Deploy istegi gonderildi." : "Deploy istegi gonderilmedi."
    return `${result.tenant_count} aktif tenant icin ${result.domains.length} domain senkronize edildi. ${deployText}`
  }

  async function handleSyncDomains() {
    setSyncingDomains(true)
    setError("")
    setActionMessage("")
    try {
      const result = await superAdminPost<TenantDomainSyncResponse>("/api/v1/superadmin/tenants/sync-domains", {})
      const message = buildDomainSyncMessage(result)
      if (!result.enabled || result.error) setError(message)
      else setActionMessage(message)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) {
        setError(err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Coolify domain sync baslatilamadi.")
      }
    } finally {
      setSyncingDomains(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-100">Tenant Management</h1>
          <p className="mt-1 text-sm text-zinc-400">Listele, filtrele, detay incele ve impersonation baslat.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleSyncDomains}
            disabled={syncingDomains}
            className="rounded-lg border border-zinc-700 px-3 py-2 text-sm font-semibold text-zinc-100 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {syncingDomains ? "Senkronize ediliyor..." : "Manuel Coolify Domain Sync"}
          </button>
          <Link
            href="/superadmin/tenants/new"
            className="rounded-lg bg-zinc-100 px-3 py-2 text-sm font-semibold text-zinc-900 hover:bg-white"
          >
            + Yeni Tenant
          </Link>
        </div>
      </div>

      <section className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 md:grid-cols-5">
        <select
          value={status}
          onChange={(event) => {
            setPage(1)
            setStatus(event.target.value as TenantStatus | "all")
          }}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        >
          <option value="all">Tum Durumlar</option>
          <option value="active">Aktif</option>
          <option value="inactive">Pasif</option>
          <option value="deleted">Silinmis</option>
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={(event) => {
            setPage(1)
            setDateFrom(event.target.value)
          }}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        />
        <input
          type="date"
          value={dateTo}
          onChange={(event) => {
            setPage(1)
            setDateTo(event.target.value)
          }}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        />
        <input
          type="text"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder="Subdomain / isim ara"
          className="md:col-span-2 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        />
      </section>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}
      {actionMessage && (
        <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {actionMessage}
        </p>
      )}

      <section className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900/70">
        <table className="min-w-full divide-y divide-zinc-800">
          <thead className="bg-zinc-900">
            <tr className="text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("subdomain")} className="hover:text-zinc-300">
                  Subdomain
                </button>
              </th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("name")} className="hover:text-zinc-300">
                  Isim
                </button>
              </th>
              <th className="px-3 py-3">Durum</th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("user_count")} className="hover:text-zinc-300">
                  User
                </button>
              </th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("booking_count")} className="hover:text-zinc-300">
                  Booking
                </button>
              </th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("created_at")} className="hover:text-zinc-300">
                  Kayit
                </button>
              </th>
              <th className="px-3 py-3">Aksiyon</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800 text-sm text-zinc-200">
            {loading && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-zinc-400">
                  Tenant listesi yukleniyor...
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-zinc-400">
                  Filtrelere uygun tenant bulunamadi.
                </td>
              </tr>
            )}
            {!loading &&
              rows.map((tenant) => (
                <tr key={tenant.id} className="hover:bg-zinc-900/60">
                  <td className="px-3 py-3 font-medium text-zinc-100">{tenant.subdomain}</td>
                  <td className="px-3 py-3">{tenant.name}</td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${getTenantStatusBadgeClass(tenant.status)}`}>
                      {getTenantStatusLabel(tenant.status)}
                    </span>
                  </td>
                  <td className="px-3 py-3">{tenant.user_count}</td>
                  <td className="px-3 py-3">{tenant.booking_count}</td>
                  <td className="px-3 py-3 text-zinc-400">{formatTenantDate(tenant.created_at)}</td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/superadmin/tenants/${tenant.id}`}
                        className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Detay
                      </Link>
                      <button
                        type="button"
                        onClick={() => handleImpersonate(tenant.id, tenant.subdomain)}
                        disabled={pendingImpersonateId === tenant.id || tenant.status === "deleted"}
                        className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {pendingImpersonateId === tenant.id ? "Aciliyor..." : "Admin Olarak Gir"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-3">
        <p className="text-xs text-zinc-400">{pageInfo}</p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            disabled={!pagination || page <= 1}
            className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Onceki
          </button>
          <button
            type="button"
            onClick={() => setPage((prev) => prev + 1)}
            disabled={!pagination || page >= pagination.total_pages}
            className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Sonraki
          </button>
        </div>
      </div>
    </div>
  )
}
