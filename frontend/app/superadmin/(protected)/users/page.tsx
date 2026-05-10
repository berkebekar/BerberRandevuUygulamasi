"use client"

import { useCallback, useEffect, useMemo, useState } from "react"

import ActionConfirmSheet from "@/components/ActionConfirmSheet"
import { SuperAdminApiError, superAdminDelete, superAdminGet, superAdminPost, superAdminPut } from "@/lib/superadmin-api"

import type {
  SuperAdminTenantSummary,
  SuperAdminUserDetailResponse,
  SuperAdminUserHardDeleteResponse,
  SuperAdminUserListItem,
  SuperAdminUserListResponse,
  UserStatus,
} from "./types"
import { buildTenantUserUrl, formatDateTime, formatUserName, getStatusBadgeClass, getStatusLabel } from "./utils"

type SortKey = "created_at" | "phone" | "first_name" | "last_name" | "booking_count" | "last_booking_at"

type PendingAction =
  | { kind: "block"; user: SuperAdminUserListItem }
  | { kind: "delete"; user: SuperAdminUserListItem }
  | null

type TenantOptionResponse = {
  items: SuperAdminTenantSummary[]
}

function buildUsersPath(params: {
  page: number
  tenantId: string
  status: UserStatus | "all"
  dateFrom: string
  dateTo: string
  search: string
  sortBy: SortKey
  sortOrder: "asc" | "desc"
}): string {
  const query = new URLSearchParams()
  query.set("page", String(params.page))
  query.set("page_size", "20")
  query.set("sort_by", params.sortBy)
  query.set("sort_order", params.sortOrder)
  if (params.tenantId) query.set("tenant_id", params.tenantId)
  if (params.status !== "all") query.set("status", params.status)
  if (params.dateFrom) query.set("date_from", params.dateFrom)
  if (params.dateTo) query.set("date_to", params.dateTo)
  if (params.search.trim()) query.set("search", params.search.trim())
  return `/api/v1/superadmin/users?${query.toString()}`
}

export default function SuperAdminUsersPage() {
  const [listData, setListData] = useState<SuperAdminUserListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  const [tenantOptions, setTenantOptions] = useState<SuperAdminTenantSummary[]>([])
  const [tenantId, setTenantId] = useState("")
  const [status, setStatus] = useState<UserStatus | "all">("all")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [searchInput, setSearchInput] = useState("")
  const [searchTerm, setSearchTerm] = useState("")
  const [sortBy, setSortBy] = useState<SortKey>("created_at")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [page, setPage] = useState(1)

  const [detailUserId, setDetailUserId] = useState<string | null>(null)
  const [detailBookingPage, setDetailBookingPage] = useState(1)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailData, setDetailData] = useState<SuperAdminUserDetailResponse | null>(null)
  const [detailError, setDetailError] = useState("")

  const [pendingAction, setPendingAction] = useState<PendingAction>(null)
  const [hardDeleteTarget, setHardDeleteTarget] = useState<SuperAdminUserDetailResponse | null>(null)
  const [blockReason, setBlockReason] = useState("")
  const [actionLoading, setActionLoading] = useState(false)
  const [impersonatingId, setImpersonatingId] = useState<string | null>(null)

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const data = await superAdminGet<SuperAdminUserListResponse>(
        buildUsersPath({ page, tenantId, status, dateFrom, dateTo, search: searchTerm, sortBy, sortOrder })
      )
      setListData(data)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Kullanici listesi su an yuklenemiyor.")
      setListData(null)
    } finally {
      setLoading(false)
    }
  }, [page, tenantId, status, dateFrom, dateTo, searchTerm, sortBy, sortOrder])

  const fetchDetail = useCallback(async (userId: string, bookingPage: number) => {
    setDetailLoading(true)
    setDetailError("")
    try {
      const data = await superAdminGet<SuperAdminUserDetailResponse>(
        `/api/v1/superadmin/users/${userId}?booking_page=${bookingPage}&booking_page_size=10`
      )
      setDetailData(data)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setDetailError(err.message)
      else if (err instanceof Error) setDetailError(err.message)
      else setDetailError("Kullanici detayi su an yuklenemiyor.")
      setDetailData(null)
    } finally {
      setDetailLoading(false)
    }
  }, [])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setPage(1)
      setSearchTerm(searchInput)
    }, 400)
    return () => window.clearTimeout(timeoutId)
  }, [searchInput])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  useEffect(() => {
    async function fetchTenantOptions() {
      try {
        const response = await superAdminGet<TenantOptionResponse>(
          "/api/v1/superadmin/tenants?page=1&page_size=100&sort_by=name&sort_order=asc"
        )
        setTenantOptions(response.items ?? [])
      } catch {
        setTenantOptions([])
      }
    }
    fetchTenantOptions()
  }, [])

  useEffect(() => {
    if (!detailUserId) return
    fetchDetail(detailUserId, detailBookingPage)
  }, [detailUserId, detailBookingPage, fetchDetail])

  const rows = listData?.items ?? []
  const pagination = listData?.pagination

  const pageInfo = useMemo(() => {
    if (!pagination) return ""
    return `${pagination.page}. sayfa / ${pagination.total_pages} - Toplam ${pagination.total} kullanici`
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

  function openDetail(userId: string) {
    setDetailUserId(userId)
    setDetailBookingPage(1)
  }

  function closeDetail() {
    setDetailUserId(null)
    setDetailData(null)
    setDetailError("")
  }

  async function refreshAfterAction() {
    await fetchUsers()
    if (detailUserId) {
      await fetchDetail(detailUserId, detailBookingPage)
    }
  }

  async function handleConfirmAction() {
    if (!pendingAction) return
    const userId = pendingAction.user.id
    setActionLoading(true)
    setError("")
    setMessage("")
    try {
      if (pendingAction.kind === "block") {
        await superAdminPut(`/api/v1/superadmin/users/${userId}/block`, { reason: blockReason.trim() || undefined })
        setMessage("Kullanici engellendi.")
      } else {
        await superAdminDelete(`/api/v1/superadmin/users/${userId}`)
        setMessage("Kullanici soft delete edildi.")
      }
      setPendingAction(null)
      setBlockReason("")
      await refreshAfterAction()
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Aksiyon tamamlanamadi.")
    } finally {
      setActionLoading(false)
    }
  }

  async function handleUnblock(userId: string) {
    setActionLoading(true)
    setError("")
    setMessage("")
    try {
      await superAdminPut(`/api/v1/superadmin/users/${userId}/unblock`, {})
      setMessage("Kullanici engeli kaldirildi.")
      await refreshAfterAction()
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Kullanici engeli kaldirilamadi.")
    } finally {
      setActionLoading(false)
    }
  }

  async function handleRestore(userId: string) {
    setActionLoading(true)
    setError("")
    setMessage("")
    try {
      await superAdminPut(`/api/v1/superadmin/users/${userId}/restore`, {})
      setMessage("Kullanici geri yuklendi.")
      await refreshAfterAction()
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Kullanici geri yuklenemedi.")
    } finally {
      setActionLoading(false)
    }
  }

  async function handleHardDelete() {
    if (!hardDeleteTarget) return
    setActionLoading(true)
    setError("")
    setDetailError("")
    setMessage("")
    try {
      await superAdminDelete<SuperAdminUserHardDeleteResponse>(`/api/v1/superadmin/users/${hardDeleteTarget.id}/hard`)
      setMessage("Kullanici kalici olarak silindi.")
      setHardDeleteTarget(null)
      closeDetail()
      await fetchUsers()
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setDetailError(err.message)
      else if (err instanceof Error) setDetailError(err.message)
      else setDetailError("Kullanici kalici olarak silinemedi.")
    } finally {
      setActionLoading(false)
    }
  }

  async function handleImpersonate(user: SuperAdminUserListItem) {
    setImpersonatingId(user.id)
    setError("")
    setMessage("")
    try {
      await superAdminPost(`/api/v1/superadmin/users/${user.id}/impersonate`, {})
      window.open(buildTenantUserUrl(user.tenant), "_blank", "noopener,noreferrer")
      setMessage("User impersonation baslatildi. Kullanici paneli yeni sekmede acildi.")
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("User impersonation baslatilamadi.")
    } finally {
      setImpersonatingId(null)
    }
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h1 className="text-xl font-bold text-zinc-100">User Management</h1>
        <p className="mt-1 text-sm text-zinc-400">Kullanicilari listele, detay goruntule ve aksiyonlari yonet.</p>
      </section>

      <section className="grid gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4 md:grid-cols-6">
        <select
          value={tenantId}
          onChange={(event) => {
            setPage(1)
            setTenantId(event.target.value)
          }}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        >
          <option value="">Tum Tenantlar</option>
          {tenantOptions.map((tenant) => (
            <option key={tenant.id} value={tenant.id}>
              {tenant.name}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(event) => {
            setPage(1)
            setStatus(event.target.value as UserStatus | "all")
          }}
          className="rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        >
          <option value="all">Tum Durumlar</option>
          <option value="active">Aktif</option>
          <option value="blocked">Engelli</option>
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
          placeholder="Telefon / ad / soyad"
          className="md:col-span-2 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
        />
      </section>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}
      {message && (
        <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {message}
        </p>
      )}

      <section className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-900/70">
        <table className="min-w-full divide-y divide-zinc-800">
          <thead className="bg-zinc-900">
            <tr className="text-left text-xs uppercase tracking-wide text-zinc-500">
              <th className="px-3 py-3">Tenant</th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("first_name")} className="hover:text-zinc-300">
                  Kullanici
                </button>
              </th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("phone")} className="hover:text-zinc-300">
                  Telefon
                </button>
              </th>
              <th className="px-3 py-3">Durum</th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("booking_count")} className="hover:text-zinc-300">
                  Booking
                </button>
              </th>
              <th className="px-3 py-3">
                <button type="button" onClick={() => handleSort("last_booking_at")} className="hover:text-zinc-300">
                  Son Booking
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
                <td colSpan={8} className="px-3 py-8 text-center text-zinc-400">
                  Kullanici listesi yukleniyor...
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-zinc-400">
                  Filtrelere uygun kullanici bulunamadi.
                </td>
              </tr>
            )}
            {!loading &&
              rows.map((user) => (
                <tr key={user.id} className="hover:bg-zinc-900/60">
                  <td className="px-3 py-3">
                    <div>
                      <p className="font-medium text-zinc-100">{user.tenant.name}</p>
                      <p className="text-xs text-zinc-500">{user.tenant.subdomain}</p>
                    </div>
                  </td>
                  <td className="px-3 py-3">{formatUserName(user.first_name, user.last_name)}</td>
                  <td className="px-3 py-3">{user.phone}</td>
                  <td className="px-3 py-3">
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${getStatusBadgeClass(user.status)}`}>
                      {getStatusLabel(user.status)}
                    </span>
                  </td>
                  <td className="px-3 py-3">{user.booking_count}</td>
                  <td className="px-3 py-3 text-zinc-400">{formatDateTime(user.last_booking_at)}</td>
                  <td className="px-3 py-3 text-zinc-400">{formatDateTime(user.created_at)}</td>
                  <td className="px-3 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => openDetail(user.id)}
                        className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
                      >
                        Detay
                      </button>
                      <button
                        type="button"
                        onClick={() => handleImpersonate(user)}
                        disabled={user.status === "deleted" || impersonatingId === user.id}
                        className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {impersonatingId === user.id ? "Aciliyor..." : "User Olarak Gir"}
                      </button>
                      {user.status !== "deleted" && (
                        <>
                          {user.status !== "blocked" ? (
                            <button
                              type="button"
                              onClick={() => {
                                setPendingAction({ kind: "block", user })
                                setBlockReason("")
                              }}
                              className="rounded border border-red-500/50 px-2 py-1 text-xs text-red-200 hover:bg-red-500/10"
                            >
                              Engelle
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleUnblock(user.id)}
                              disabled={actionLoading}
                              className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800 disabled:opacity-60"
                            >
                              Engel Kaldir
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => setPendingAction({ kind: "delete", user })}
                            className="rounded border border-red-500/50 px-2 py-1 text-xs text-red-200 hover:bg-red-500/10"
                          >
                            Soft Delete
                          </button>
                        </>
                      )}
                      {user.status === "deleted" && (
                        <button
                          type="button"
                          onClick={() => handleRestore(user.id)}
                          disabled={actionLoading}
                          className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800 disabled:opacity-60"
                        >
                          Geri Yukle
                        </button>
                      )}
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

      <ActionConfirmSheet
        open={pendingAction !== null}
        title={pendingAction?.kind === "block" ? "Kullaniciyi Engelle" : "Kullaniciyi Soft Delete Et"}
        description={
          pendingAction
            ? `${formatUserName(pendingAction.user.first_name, pendingAction.user.last_name)} icin bu aksiyon uygulanacak.`
            : ""
        }
        confirmText={pendingAction?.kind === "block" ? "Engelle" : "Soft Delete"}
        confirmTone="danger"
        isLoading={actionLoading}
        onCancel={() => {
          if (actionLoading) return
          setPendingAction(null)
          setBlockReason("")
        }}
        onConfirm={handleConfirmAction}
      >
        {pendingAction?.kind === "block" && (
          <textarea
            value={blockReason}
            onChange={(event) => setBlockReason(event.target.value)}
            rows={2}
            placeholder="Sebep notu (opsiyonel)"
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
          />
        )}
      </ActionConfirmSheet>

      {detailUserId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-4xl rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-zinc-100">Kullanici Detayi</h2>
              <button
                type="button"
                onClick={closeDetail}
                className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800"
              >
                Kapat
              </button>
            </div>

            {detailLoading && <p className="text-sm text-zinc-400">Detaylar yukleniyor...</p>}
            {!detailLoading && detailError && <p className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{detailError}</p>}
            {!detailLoading && detailData && (
              <div className="space-y-4">
                <section className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 text-sm text-zinc-300">
                    <p className="font-medium text-zinc-100">{formatUserName(detailData.first_name, detailData.last_name)}</p>
                    <p>Telefon: {detailData.phone}</p>
                    <p>Status: {getStatusLabel(detailData.status)}</p>
                    <p>Kayit: {formatDateTime(detailData.created_at)}</p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 text-sm text-zinc-300">
                    <p className="font-medium text-zinc-100">Tenant</p>
                    <p>{detailData.tenant.name}</p>
                    <p className="text-zinc-400">{detailData.tenant.subdomain}</p>
                  </div>
                </section>

                <section className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-500/30 bg-red-500/5 p-3">
                  <div>
                    <h3 className="text-sm font-semibold text-red-100">Kalici Silme</h3>
                    <p className="mt-1 text-sm text-red-200/80">User, booking gecmisi ve user OTP kayitlari DB&apos;den silinir.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setHardDeleteTarget(detailData)}
                    disabled={actionLoading}
                    className="rounded border border-red-500/60 px-3 py-2 text-sm font-semibold text-red-100 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    Hard Delete
                  </button>
                </section>

                <section className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <h3 className="text-sm font-semibold text-zinc-100">Booking Gecmisi</h3>
                  {detailData.bookings.items.length === 0 ? (
                    <p className="mt-2 text-sm text-zinc-400">Booking kaydi bulunamadi.</p>
                  ) : (
                    <div className="mt-2 overflow-x-auto">
                      <table className="min-w-full divide-y divide-zinc-800 text-sm">
                        <thead className="text-left text-xs uppercase tracking-wide text-zinc-500">
                          <tr>
                            <th className="py-2 pr-3">Slot</th>
                            <th className="py-2 pr-3">Durum</th>
                            <th className="py-2 pr-3">Iptal Eden</th>
                            <th className="py-2">Olusma</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800 text-zinc-200">
                          {detailData.bookings.items.map((booking) => (
                            <tr key={booking.id}>
                              <td className="py-2 pr-3">{formatDateTime(booking.slot_time)}</td>
                              <td className="py-2 pr-3">{booking.status}</td>
                              <td className="py-2 pr-3">{booking.cancelled_by ?? "-"}</td>
                              <td className="py-2">{formatDateTime(booking.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="mt-3 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setDetailBookingPage((prev) => Math.max(1, prev - 1))}
                      disabled={detailData.bookings.pagination.page <= 1}
                      className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800 disabled:opacity-60"
                    >
                      Onceki
                    </button>
                    <button
                      type="button"
                      onClick={() => setDetailBookingPage((prev) => prev + 1)}
                      disabled={detailData.bookings.pagination.page >= detailData.bookings.pagination.total_pages}
                      className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-200 hover:bg-zinc-800 disabled:opacity-60"
                    >
                      Sonraki
                    </button>
                  </div>
                </section>

                <section className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
                  <h3 className="text-sm font-semibold text-zinc-100">OTP Istekleri (Son 10)</h3>
                  {detailData.otp_requests.length === 0 ? (
                    <p className="mt-2 text-sm text-zinc-400">OTP istegi bulunamadi.</p>
                  ) : (
                    <ul className="mt-2 space-y-2">
                      {detailData.otp_requests.map((otp) => (
                        <li key={otp.id} className="rounded border border-zinc-800 px-3 py-2 text-sm text-zinc-300">
                          <p>Olusma: {formatDateTime(otp.created_at)}</p>
                          <p>Bitis: {formatDateTime(otp.expires_at)}</p>
                          <p>Kullanildi: {otp.is_used ? "Evet" : "Hayir"} | Deneme: {otp.attempt_count}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            )}
          </div>
        </div>
      )}

      <ActionConfirmSheet
        open={hardDeleteTarget !== null}
        title="Kullaniciyi Kalici Olarak Sil"
        description={
          hardDeleteTarget
            ? `${formatUserName(hardDeleteTarget.first_name, hardDeleteTarget.last_name)} DB'den kalici olarak silinecek.`
            : ""
        }
        confirmText="Hard Delete"
        confirmTone="danger"
        isLoading={actionLoading}
        onCancel={() => {
          if (actionLoading) return
          setHardDeleteTarget(null)
        }}
        onConfirm={handleHardDelete}
      />
    </div>
  )
}
