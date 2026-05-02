"use client"

import { useEffect, useMemo, useState } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"

import VirtualizedList from "@/components/VirtualizedList"
import { SuperAdminApiError, superAdminGet } from "@/lib/superadmin-api"

type PaginationMeta = {
  page: number
  page_size: number
  total: number
  total_pages: number
}

type ActivityLogItem = {
  id: string
  super_admin_id: string | null
  action_type: string
  entity_type: string
  entity_id: string | null
  tenant_id: string | null
  metadata_json: Record<string, unknown> | null
  created_at: string
}

type ActivityLogListResponse = {
  items: ActivityLogItem[]
  pagination: PaginationMeta
}

type TenantOption = {
  id: string
  name: string
}

type TenantListResponse = {
  items: TenantOption[]
}

type SortBy = "created_at" | "action_type"
type SortOrder = "asc" | "desc"

const DEFAULTS = {
  page: 1,
  pageSize: 50,
  sortBy: "created_at" as SortBy,
  sortOrder: "desc" as SortOrder,
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  })
}

function parseIntParam(value: string | null, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback
  return Math.floor(parsed)
}

export default function SuperAdminActivityLogsPage() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [listData, setListData] = useState<ActivityLogListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const [tenantOptions, setTenantOptions] = useState<TenantOption[]>([])

  const [qInput, setQInput] = useState("")
  const [actionInput, setActionInput] = useState("")

  const params = useMemo(() => {
    const page = parseIntParam(searchParams.get("page"), DEFAULTS.page)
    const pageSize = Math.min(parseIntParam(searchParams.get("page_size"), DEFAULTS.pageSize), 100)
    const sortByRaw = searchParams.get("sort_by")
    const sortBy: SortBy = sortByRaw === "action_type" ? "action_type" : DEFAULTS.sortBy
    const sortOrder: SortOrder = searchParams.get("sort_order") === "asc" ? "asc" : "desc"

    return {
      page,
      pageSize,
      sortBy,
      sortOrder,
      actionType: searchParams.get("action_type") ?? "",
      tenantId: searchParams.get("tenant_id") ?? "",
      superAdminId: searchParams.get("super_admin_id") ?? "",
      dateFrom: searchParams.get("date_from") ?? "",
      dateTo: searchParams.get("date_to") ?? "",
      q: searchParams.get("q") ?? "",
    }
  }, [searchParams])

  useEffect(() => {
    setQInput(params.q)
  }, [params.q])

  useEffect(() => {
    setActionInput(params.actionType)
  }, [params.actionType])

  function replaceParams(updater: (next: URLSearchParams) => void) {
    const next = new URLSearchParams(searchParams.toString())
    updater(next)
    const nextQuery = next.toString()
    if (nextQuery === searchParams.toString()) return
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname)
  }

  useEffect(() => {
    if (qInput === params.q) return
    const timer = window.setTimeout(() => {
      replaceParams((next) => {
        if (qInput.trim()) next.set("q", qInput.trim())
        else next.delete("q")
        next.set("page", "1")
      })
    }, 350)

    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qInput])

  useEffect(() => {
    if (actionInput === params.actionType) return
    const timer = window.setTimeout(() => {
      replaceParams((next) => {
        if (actionInput.trim()) next.set("action_type", actionInput.trim())
        else next.delete("action_type")
        next.set("page", "1")
      })
    }, 350)

    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actionInput])

  useEffect(() => {
    let mounted = true

    async function fetchTenants() {
      try {
        const response = await superAdminGet<TenantListResponse>(
          "/api/v1/superadmin/tenants?page=1&page_size=100&sort_by=name&sort_order=asc"
        )
        if (mounted) setTenantOptions(response.items ?? [])
      } catch {
        if (mounted) setTenantOptions([])
      }
    }

    fetchTenants()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    let mounted = true

    async function fetchList() {
      setLoading(true)
      setError("")

      const query = new URLSearchParams()
      query.set("page", String(params.page))
      query.set("page_size", String(params.pageSize))
      if (params.actionType) query.set("action_type", params.actionType)
      if (params.tenantId) query.set("tenant_id", params.tenantId)
      if (params.superAdminId) query.set("super_admin_id", params.superAdminId)
      if (params.dateFrom) query.set("date_from", params.dateFrom)
      if (params.dateTo) query.set("date_to", params.dateTo)

      try {
        const data = await superAdminGet<ActivityLogListResponse>(`/api/v1/superadmin/logs/activities?${query.toString()}`)
        if (mounted) setListData(data)
      } catch (err: unknown) {
        if (!mounted) return
        if (err instanceof SuperAdminApiError) setError(err.message)
        else if (err instanceof Error) setError(err.message)
        else setError("Activity log listesi yuklenemedi.")
        setListData(null)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    fetchList()
    return () => {
      mounted = false
    }
  }, [params])

  function updateSimpleParam(key: string, value: string) {
    replaceParams((next) => {
      if (value) next.set(key, value)
      else next.delete(key)
      next.set("page", "1")
    })
  }

  function toggleSort(column: SortBy) {
    replaceParams((next) => {
      if (params.sortBy === column) {
        next.set("sort_order", params.sortOrder === "asc" ? "desc" : "asc")
      } else {
        next.set("sort_by", column)
        next.set("sort_order", "desc")
      }
      next.set("page", "1")
    })
  }

  const filteredAndSortedItems = useMemo(() => {
    let items = [...(listData?.items ?? [])]

    if (params.q.trim()) {
      const needle = params.q.trim().toLowerCase()
      items = items.filter((item) => {
        return [
          item.action_type,
          item.entity_type,
          item.entity_id ?? "",
          item.tenant_id ?? "",
          item.super_admin_id ?? "",
          JSON.stringify(item.metadata_json ?? {}),
        ]
          .join(" ")
          .toLowerCase()
          .includes(needle)
      })
    }

    const direction = params.sortOrder === "asc" ? 1 : -1
    items.sort((a, b) => {
      if (params.sortBy === "action_type") return a.action_type.localeCompare(b.action_type) * direction
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * direction
    })

    return items
  }, [listData?.items, params.q, params.sortBy, params.sortOrder])

  const pagination = listData?.pagination

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h1 className="text-xl font-bold text-zinc-100">Activity Logs</h1>
        <p className="mt-1 text-sm text-zinc-400">Aksiyonlari filtrele, sirala ve zaman cizelgesinde incele.</p>
      </section>

      <section className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 md:grid-cols-4 xl:grid-cols-8">
        <input
          value={actionInput}
          onChange={(event) => setActionInput(event.target.value)}
          placeholder="Action type"
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />

        <select
          value={params.tenantId}
          onChange={(event) => updateSimpleParam("tenant_id", event.target.value)}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        >
          <option value="">Tum tenantlar</option>
          {tenantOptions.map((tenant) => (
            <option key={tenant.id} value={tenant.id}>
              {tenant.name}
            </option>
          ))}
        </select>

        <input
          value={params.superAdminId}
          onChange={(event) => updateSimpleParam("super_admin_id", event.target.value)}
          placeholder="Super admin id"
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />

        <input
          type="date"
          value={params.dateFrom}
          onChange={(event) => updateSimpleParam("date_from", event.target.value)}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />

        <input
          type="date"
          value={params.dateTo}
          onChange={(event) => updateSimpleParam("date_to", event.target.value)}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />

        <select
          value={String(params.pageSize)}
          onChange={(event) =>
            replaceParams((next) => {
              next.set("page_size", event.target.value)
              next.set("page", "1")
            })
          }
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        >
          <option value="20">20 / sayfa</option>
          <option value="50">50 / sayfa</option>
          <option value="100">100 / sayfa</option>
        </select>

        <button
          type="button"
          onClick={() => toggleSort("created_at")}
          className="rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-100"
        >
          Tarih: {params.sortBy === "created_at" ? params.sortOrder : "-"}
        </button>

        <input
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
          placeholder="Ara (local quick filter)"
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />
      </section>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}

      <section className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/70">
        <div className="grid grid-cols-[170px_190px_160px_160px_1fr] gap-2 border-b border-zinc-800 bg-zinc-900 px-3 py-2 text-xs uppercase tracking-wide text-zinc-500">
          <button type="button" onClick={() => toggleSort("created_at")} className="text-left hover:text-zinc-300">
            Tarih
          </button>
          <button type="button" onClick={() => toggleSort("action_type")} className="text-left hover:text-zinc-300">
            Action
          </button>
          <div>Tenant</div>
          <div>Entity</div>
          <div>Metadata</div>
        </div>

        {loading ? (
          <div className="px-3 py-10 text-center text-sm text-zinc-400">Activity loglar yukleniyor...</div>
        ) : (
          <VirtualizedList
            items={filteredAndSortedItems}
            height={520}
            rowHeight={72}
            overscan={8}
            className="px-1"
            getKey={(item) => item.id}
            renderItem={(item) => (
              <div className="grid h-full grid-cols-[170px_190px_160px_160px_1fr] items-center gap-2 border-b border-zinc-800/80 px-2 text-sm text-zinc-200">
                <span className="text-zinc-400">{formatDateTime(item.created_at)}</span>
                <div>
                  <p className="font-medium text-zinc-100">{item.action_type}</p>
                  <p className="text-xs text-zinc-500">super_admin: {item.super_admin_id ?? "-"}</p>
                </div>
                <span className="truncate text-zinc-400">{item.tenant_id ?? "-"}</span>
                <div>
                  <p>{item.entity_type}</p>
                  <p className="truncate text-xs text-zinc-500">{item.entity_id ?? "-"}</p>
                </div>
                <pre className="max-h-14 overflow-auto whitespace-pre-wrap text-xs text-zinc-400">
                  {JSON.stringify(item.metadata_json ?? {}, null, 2)}
                </pre>
              </div>
            )}
          />
        )}
      </section>

      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-3">
        <p className="text-xs text-zinc-400">
          {pagination
            ? `${pagination.page}. sayfa / ${pagination.total_pages} - Toplam ${pagination.total} kayit`
            : "Sayfalama bilgisi yok"}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() =>
              replaceParams((next) => {
                next.set("page", String(Math.max(1, params.page - 1)))
              })
            }
            disabled={!pagination || params.page <= 1}
            className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 disabled:opacity-60"
          >
            Onceki
          </button>
          <button
            type="button"
            onClick={() =>
              replaceParams((next) => {
                next.set("page", String(params.page + 1))
              })
            }
            disabled={!pagination || params.page >= pagination.total_pages}
            className="rounded border border-zinc-700 px-3 py-1.5 text-sm text-zinc-200 disabled:opacity-60"
          >
            Sonraki
          </button>
        </div>
      </section>
    </div>
  )
}
