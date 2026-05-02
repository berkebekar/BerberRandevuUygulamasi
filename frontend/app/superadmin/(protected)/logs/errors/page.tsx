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

type ErrorLogListItem = {
  id: string
  tenant_id: string | null
  request_id: string | null
  endpoint: string
  method: string
  status_code: number
  error_code: string | null
  message: string
  created_at: string
}

type ErrorLogListResponse = {
  items: ErrorLogListItem[]
  pagination: PaginationMeta
}

type ErrorLogDetailResponse = {
  id: string
  tenant_id: string | null
  request_id: string | null
  endpoint: string
  method: string
  status_code: number
  error_code: string | null
  message: string
  stack_trace: string | null
  request_meta: Record<string, unknown> | null
  created_at: string
}

type TenantOption = {
  id: string
  name: string
}

type TenantListResponse = {
  items: TenantOption[]
}

type SortBy = "created_at" | "status_code" | "endpoint" | "method"
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

function getStatusBadgeClass(statusCode: number): string {
  if (statusCode >= 500) return "border-red-500/40 bg-red-500/10 text-red-300"
  if (statusCode >= 400) return "border-amber-500/40 bg-amber-500/10 text-amber-300"
  return "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
}

function maskSensitive(value: unknown): unknown {
  const sensitiveTokens = ["password", "token", "cookie", "secret", "otp", "code", "authorization"]
  if (Array.isArray(value)) {
    return value.map(maskSensitive)
  }
  if (value && typeof value === "object") {
    const output: Record<string, unknown> = {}
    for (const [key, item] of Object.entries(value)) {
      const lower = key.toLowerCase()
      if (sensitiveTokens.some((token) => lower.includes(token))) {
        output[key] = "***"
      } else {
        output[key] = maskSensitive(item)
      }
    }
    return output
  }
  return value
}

function parseIntParam(value: string | null, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback
  return Math.floor(parsed)
}

export default function SuperAdminErrorLogsPage() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const [listData, setListData] = useState<ErrorLogListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  const [tenantOptions, setTenantOptions] = useState<TenantOption[]>([])

  const [qInput, setQInput] = useState("")
  const [endpointInput, setEndpointInput] = useState("")

  const [selectedErrorId, setSelectedErrorId] = useState<string | null>(null)
  const [detailData, setDetailData] = useState<ErrorLogDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState("")

  const params = useMemo(() => {
    const page = parseIntParam(searchParams.get("page"), DEFAULTS.page)
    const pageSize = Math.min(parseIntParam(searchParams.get("page_size"), DEFAULTS.pageSize), 100)
    const sortByRaw = searchParams.get("sort_by")
    const sortBy: SortBy = sortByRaw === "status_code" || sortByRaw === "endpoint" || sortByRaw === "method" ? sortByRaw : DEFAULTS.sortBy
    const sortOrder: SortOrder = searchParams.get("sort_order") === "asc" ? "asc" : "desc"

    return {
      page,
      pageSize,
      sortBy,
      sortOrder,
      tenantId: searchParams.get("tenant_id") ?? "",
      endpoint: searchParams.get("endpoint") ?? "",
      statusCode: searchParams.get("status_code") ?? "",
      dateFrom: searchParams.get("date_from") ?? "",
      dateTo: searchParams.get("date_to") ?? "",
      errorCode: searchParams.get("error_code") ?? "",
      q: searchParams.get("q") ?? "",
    }
  }, [searchParams])

  useEffect(() => {
    setQInput(params.q)
  }, [params.q])

  useEffect(() => {
    setEndpointInput(params.endpoint)
  }, [params.endpoint])

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
    if (endpointInput === params.endpoint) return
    const timer = window.setTimeout(() => {
      replaceParams((next) => {
        if (endpointInput.trim()) next.set("endpoint", endpointInput.trim())
        else next.delete("endpoint")
        next.set("page", "1")
      })
    }, 350)

    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpointInput])

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
      if (params.tenantId) query.set("tenant_id", params.tenantId)
      if (params.endpoint) query.set("endpoint", params.endpoint)
      if (params.statusCode) query.set("status_code", params.statusCode)
      if (params.dateFrom) query.set("date_from", params.dateFrom)
      if (params.dateTo) query.set("date_to", params.dateTo)
      if (params.errorCode) query.set("error_code", params.errorCode)
      if (params.q) query.set("q", params.q)

      try {
        const data = await superAdminGet<ErrorLogListResponse>(`/api/v1/superadmin/logs/errors?${query.toString()}`)
        if (mounted) setListData(data)
      } catch (err: unknown) {
        if (!mounted) return
        if (err instanceof SuperAdminApiError) setError(err.message)
        else if (err instanceof Error) setError(err.message)
        else setError("Error log listesi yuklenemedi.")
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

  useEffect(() => {
    if (!selectedErrorId) {
      setDetailData(null)
      setDetailError("")
      return
    }

    let mounted = true

    async function fetchDetail() {
      setDetailLoading(true)
      setDetailError("")
      try {
        const data = await superAdminGet<ErrorLogDetailResponse>(`/api/v1/superadmin/logs/errors/${selectedErrorId}`)
        if (mounted) {
          data.request_meta = maskSensitive(data.request_meta) as Record<string, unknown> | null
          setDetailData(data)
        }
      } catch (err: unknown) {
        if (!mounted) return
        if (err instanceof SuperAdminApiError) setDetailError(err.message)
        else if (err instanceof Error) setDetailError(err.message)
        else setDetailError("Hata detayi yuklenemedi.")
        setDetailData(null)
      } finally {
        if (mounted) setDetailLoading(false)
      }
    }

    fetchDetail()
    return () => {
      mounted = false
    }
  }, [selectedErrorId])

  const sortedItems = useMemo(() => {
    const items = [...(listData?.items ?? [])]
    const direction = params.sortOrder === "asc" ? 1 : -1

    items.sort((a, b) => {
      if (params.sortBy === "status_code") return (a.status_code - b.status_code) * direction
      if (params.sortBy === "endpoint") return a.endpoint.localeCompare(b.endpoint) * direction
      if (params.sortBy === "method") return a.method.localeCompare(b.method) * direction
      return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * direction
    })

    return items
  }, [listData?.items, params.sortBy, params.sortOrder])

  function updateSimpleParam(key: string, value: string) {
    replaceParams((next) => {
      if (value) next.set(key, value)
      else next.delete(key)
      next.set("page", "1")
    })
  }

  function toggleSort(column: SortBy) {
    replaceParams((next) => {
      const currentBy = params.sortBy
      const currentOrder = params.sortOrder
      if (currentBy === column) {
        next.set("sort_order", currentOrder === "asc" ? "desc" : "asc")
      } else {
        next.set("sort_by", column)
        next.set("sort_order", "desc")
      }
      next.set("page", "1")
    })
  }

  const pagination = listData?.pagination

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h1 className="text-xl font-bold text-zinc-100">Error Logs</h1>
        <p className="mt-1 text-sm text-zinc-400">Hata kayitlarini filtrele, sirala ve detaylarini incele.</p>
      </section>

      <section className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 md:grid-cols-4 xl:grid-cols-8">
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
          value={endpointInput}
          onChange={(event) => setEndpointInput(event.target.value)}
          placeholder="Endpoint"
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />

        <input
          value={params.statusCode}
          onChange={(event) => updateSimpleParam("status_code", event.target.value.replace(/[^0-9]/g, ""))}
          placeholder="Status"
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />

        <input
          value={params.errorCode}
          onChange={(event) => updateSimpleParam("error_code", event.target.value)}
          placeholder="Error code"
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

        <input
          value={qInput}
          onChange={(event) => setQInput(event.target.value)}
          placeholder="Ara (mesaj/endpoint)"
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
        />
      </section>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}

      <section className="overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/70">
        <div className="grid grid-cols-[170px_170px_1.4fr_120px_90px_140px_2fr] gap-2 border-b border-zinc-800 bg-zinc-900 px-3 py-2 text-xs uppercase tracking-wide text-zinc-500">
          <button type="button" onClick={() => toggleSort("created_at")} className="text-left hover:text-zinc-300">
            Tarih
          </button>
          <div>Tenant</div>
          <button type="button" onClick={() => toggleSort("endpoint")} className="text-left hover:text-zinc-300">
            Endpoint
          </button>
          <button type="button" onClick={() => toggleSort("method")} className="text-left hover:text-zinc-300">
            Method
          </button>
          <button type="button" onClick={() => toggleSort("status_code")} className="text-left hover:text-zinc-300">
            Status
          </button>
          <div>Error Code</div>
          <div>Message</div>
        </div>

        {loading ? (
          <div className="px-3 py-10 text-center text-sm text-zinc-400">Error loglar yukleniyor...</div>
        ) : (
          <VirtualizedList
            items={sortedItems}
            height={520}
            rowHeight={56}
            overscan={8}
            className="px-1"
            getKey={(item) => item.id}
            renderItem={(item) => (
              <button
                type="button"
                onClick={() => setSelectedErrorId(item.id)}
                className="grid w-full grid-cols-[170px_170px_1.4fr_120px_90px_140px_2fr] items-center gap-2 border-b border-zinc-800/80 px-2 text-left text-sm text-zinc-200 hover:bg-zinc-800/40"
              >
                <span className="text-zinc-400">{formatDateTime(item.created_at)}</span>
                <span className="truncate text-zinc-400">{item.tenant_id ?? "-"}</span>
                <span className="truncate">{item.endpoint}</span>
                <span>{item.method}</span>
                <span className={`inline-flex w-fit rounded-full border px-2 py-0.5 text-xs ${getStatusBadgeClass(item.status_code)}`}>
                  {item.status_code}
                </span>
                <span className="truncate text-zinc-400">{item.error_code ?? "-"}</span>
                <span className="truncate text-zinc-300">{item.message}</span>
              </button>
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

      {selectedErrorId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-4xl rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-zinc-100">Hata Detayi</h2>
              <button
                type="button"
                onClick={() => setSelectedErrorId(null)}
                className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200"
              >
                Kapat
              </button>
            </div>

            {detailLoading && <p className="text-sm text-zinc-400">Detay yukleniyor...</p>}
            {!detailLoading && detailError && (
              <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{detailError}</p>
            )}

            {!detailLoading && detailData && (
              <div className="space-y-4 text-sm">
                <section className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 text-zinc-300">
                    <p>Endpoint: {detailData.endpoint}</p>
                    <p>Method: {detailData.method}</p>
                    <p>Status: {detailData.status_code}</p>
                    <p>Request ID: {detailData.request_id ?? "-"}</p>
                    <p>Tenant ID: {detailData.tenant_id ?? "-"}</p>
                    <p>Tarih: {formatDateTime(detailData.created_at)}</p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 text-zinc-300">
                    <p className="font-medium text-zinc-100">Mesaj</p>
                    <p className="mt-1 whitespace-pre-wrap break-words">{detailData.message}</p>
                    <p className="mt-2 text-xs text-zinc-400">Error Code: {detailData.error_code ?? "-"}</p>
                  </div>
                </section>

                <section className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="mb-2 font-medium text-zinc-100">Stack Trace</p>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
                    {detailData.stack_trace ?? "-"}
                  </pre>
                </section>

                <section className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <p className="mb-2 font-medium text-zinc-100">Request Details (Masked)</p>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-300">
                    {JSON.stringify(maskSensitive(detailData.request_meta), null, 2)}
                  </pre>
                </section>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
