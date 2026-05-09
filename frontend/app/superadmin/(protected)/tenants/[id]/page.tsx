"use client"

import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

import {
  SuperAdminApiError,
  superAdminDelete,
  superAdminGet,
  superAdminPost,
  superAdminPut,
} from "@/lib/superadmin-api"

import type { TenantDetailResponse, TenantStatus } from "../types"
import { buildTenantAdminUrl, formatTenantDate, getTenantStatusBadgeClass, getTenantStatusLabel } from "../utils"

type EditableFields = {
  subdomain: string
  name: string
  admin_phone: string
  admin_email: string
}

export default function SuperAdminTenantDetailPage() {
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const tenantId = String(params.id)

  const [tenant, setTenant] = useState<TenantDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")
  const [saving, setSaving] = useState(false)
  const [isEditOpen, setIsEditOpen] = useState(false)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [hardDeleteConfirmOpen, setHardDeleteConfirmOpen] = useState(false)
  const [statusReason, setStatusReason] = useState("")
  const [copied, setCopied] = useState(false)

  const waPhone = process.env.NEXT_PUBLIC_WA_PHONE_NUMBER ?? ""

  function handleCopyLink() {
    if (!tenant || !waPhone) return
    navigator.clipboard.writeText(`https://wa.me/${waPhone}?text=${tenant.subdomain}`)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  const [editValues, setEditValues] = useState<EditableFields>({
    subdomain: "",
    name: "",
    admin_phone: "",
    admin_email: "",
  })

  async function fetchTenantDetail() {
    setLoading(true)
    setError("")
    try {
      const data = await superAdminGet<TenantDetailResponse>(`/api/v1/superadmin/tenants/${tenantId}`)
      setTenant(data)
      setEditValues({
        subdomain: data.subdomain,
        name: data.name,
        admin_phone: data.admin?.phone ?? "",
        admin_email: data.admin?.email ?? "",
      })
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Tenant detaylari su an yuklenemiyor.")
      setTenant(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTenantDetail()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId])

  const nextStatus = useMemo<TenantStatus | null>(() => {
    if (!tenant) return null
    if (tenant.status === "active") return "inactive"
    if (tenant.status === "inactive") return "active"
    return null
  }, [tenant])

  async function handleSaveEdit() {
    if (!tenant) return
    setSaving(true)
    setError("")
    setMessage("")
    try {
      const payload = {
        subdomain: editValues.subdomain.trim(),
        name: editValues.name.trim(),
        admin_phone: editValues.admin_phone.trim() || undefined,
        admin_email: editValues.admin_email.trim() || undefined,
      }
      const updated = await superAdminPut<TenantDetailResponse>(`/api/v1/superadmin/tenants/${tenant.id}`, payload)
      setTenant(updated)
      setIsEditOpen(false)
      setMessage("Tenant bilgileri guncellendi.")
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Tenant guncellenemedi.")
    } finally {
      setSaving(false)
    }
  }

  async function handleToggleStatus() {
    if (!tenant || !nextStatus) return
    setSaving(true)
    setError("")
    setMessage("")
    try {
      await superAdminPut(`/api/v1/superadmin/tenants/${tenant.id}/status`, {
        status: nextStatus,
        reason: statusReason.trim() || undefined,
      })
      await fetchTenantDetail()
      setStatusReason("")
      setMessage(`Tenant durumu ${getTenantStatusLabel(nextStatus)} olarak guncellendi.`)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Tenant durumu guncellenemedi.")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!tenant) return
    setSaving(true)
    setError("")
    setMessage("")
    try {
      await superAdminDelete(`/api/v1/superadmin/tenants/${tenant.id}`)
      setDeleteConfirmOpen(false)
      setMessage("Tenant silindi olarak isaretlendi.")
      await fetchTenantDetail()
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Tenant silinemedi.")
    } finally {
      setSaving(false)
    }
  }

  async function handleHardDelete() {
    if (!tenant) return
    setSaving(true)
    setError("")
    setMessage("")
    try {
      await superAdminDelete(`/api/v1/superadmin/tenants/${tenant.id}/hard`)
      setHardDeleteConfirmOpen(false)
      router.push("/superadmin/tenants")
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Tenant kalici olarak silinemedi.")
    } finally {
      setSaving(false)
    }
  }

  async function handleImpersonate() {
    if (!tenant) return
    setSaving(true)
    setError("")
    setMessage("")
    try {
      await superAdminPost(`/api/v1/superadmin/tenants/${tenant.id}/impersonate`, {})
      window.open(buildTenantAdminUrl(tenant.subdomain), "_blank", "noopener,noreferrer")
      setMessage("Impersonation baslatildi. Tenant admin paneli yeni sekmede acildi.")
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Impersonation baslatilamadi.")
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-5 text-sm text-zinc-400">Tenant detaylari yukleniyor...</div>
  }

  if (!tenant) {
    return (
      <div className="space-y-3">
        <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
          {error || "Tenant bulunamadi."}
        </p>
        <Link href="/superadmin/tenants" className="inline-flex rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800">
          Listeye don
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <div>
          <button
            type="button"
            onClick={() => router.push("/superadmin/tenants")}
            className="mb-2 text-xs text-zinc-400 hover:text-zinc-200"
          >
            ← Tenant listesine don
          </button>
          <h1 className="text-xl font-bold text-zinc-100">{tenant.name}</h1>
          <p className="text-sm text-zinc-400">{tenant.subdomain}</p>
        </div>
        <span className={`rounded-full border px-2 py-1 text-xs ${getTenantStatusBadgeClass(tenant.status)}`}>
          {getTenantStatusLabel(tenant.status)}
        </span>
      </div>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}
      {message && (
        <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {message}
        </p>
      )}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Kullanicilar</p>
          <p className="mt-2 text-2xl font-bold text-zinc-100">{tenant.stats.user_count}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Toplam Booking</p>
          <p className="mt-2 text-2xl font-bold text-zinc-100">{tenant.stats.booking_count_total}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Bu Ay Booking</p>
          <p className="mt-2 text-2xl font-bold text-zinc-100">{tenant.stats.booking_count_this_month}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
          <p className="text-xs uppercase tracking-wide text-zinc-500">Iptal Orani</p>
          <p className="mt-2 text-2xl font-bold text-zinc-100">{tenant.stats.cancel_rate.toFixed(1)}%</p>
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">Admin Bilgileri</h2>
        <div className="mt-3 grid gap-2 text-sm text-zinc-300">
          <p>Email: {tenant.admin?.email ?? "-"}</p>
          <p>Telefon: {tenant.admin?.phone ?? "-"}</p>
          <p>Kayit: {formatTenantDate(tenant.created_at)}</p>
        </div>
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">WhatsApp Bot Linki</h2>
        {waPhone ? (
          <div className="mt-3 space-y-2">
            <p className="text-xs text-zinc-400">
              Bu linki berbere gonderin. Musteriler bu link uzerinden randevu alabilir.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded bg-zinc-950 px-3 py-2 text-sm text-emerald-300">
                {`https://wa.me/${waPhone}?text=${tenant.subdomain}`}
              </code>
              <button
                type="button"
                onClick={handleCopyLink}
                className="shrink-0 rounded border border-zinc-700 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
              >
                {copied ? "Kopyalandi!" : "Kopyala"}
              </button>
            </div>
          </div>
        ) : (
          <p className="mt-2 text-xs text-amber-400">
            NEXT_PUBLIC_WA_PHONE_NUMBER env degiskeni ayarlanmamis.
          </p>
        )}
      </section>

      <section className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <h2 className="text-sm font-semibold text-zinc-100">Aksiyonlar</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setIsEditOpen(true)}
            className="rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
          >
            Duzenle
          </button>
          <button
            type="button"
            onClick={handleImpersonate}
            disabled={saving || tenant.status === "deleted"}
            className="rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Admin Olarak Gir
          </button>
          <button
            type="button"
            onClick={() => setDeleteConfirmOpen(true)}
            disabled={saving || tenant.status === "deleted"}
            className="rounded border border-red-500/50 px-3 py-2 text-sm text-red-200 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Silindi Olarak Isaretle
          </button>
          <button
            type="button"
            onClick={() => setHardDeleteConfirmOpen(true)}
            disabled={saving}
            className="rounded bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Kalici Olarak Sil
          </button>
        </div>

        {nextStatus && (
          <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
            <p className="text-sm font-medium text-zinc-200">
              Durumu {getTenantStatusLabel(nextStatus)} yapmak icin sebep (opsiyonel)
            </p>
            <textarea
              value={statusReason}
              onChange={(event) => setStatusReason(event.target.value)}
              rows={2}
              className="mt-2 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
            <button
              type="button"
              onClick={handleToggleStatus}
              disabled={saving}
              className="mt-2 rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Durumu {getTenantStatusLabel(nextStatus)} Yap
            </button>
          </div>
        )}
      </section>

      {isEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <h3 className="text-base font-semibold text-zinc-100">Tenant Duzenle</h3>
            <div className="mt-3 space-y-3">
              <input
                value={editValues.subdomain}
                onChange={(event) => setEditValues((prev) => ({ ...prev, subdomain: event.target.value }))}
                placeholder="Subdomain"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
              />
              <input
                value={editValues.name}
                onChange={(event) => setEditValues((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="Isletme adi"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
              />
              <input
                value={editValues.admin_phone}
                onChange={(event) => setEditValues((prev) => ({ ...prev, admin_phone: event.target.value }))}
                placeholder="Admin telefon"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
              />
              <input
                value={editValues.admin_email}
                onChange={(event) => setEditValues((prev) => ({ ...prev, admin_email: event.target.value }))}
                placeholder="Admin email"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsEditOpen(false)}
                className="rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
              >
                Vazgec
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                disabled={saving}
                className="rounded bg-zinc-100 px-3 py-2 text-sm font-semibold text-zinc-900 hover:bg-white disabled:opacity-60"
              >
                {saving ? "Kaydediliyor..." : "Kaydet"}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900 p-4">
            <h3 className="text-base font-semibold text-zinc-100">Tenant Silindi Olarak Isaretle</h3>
            <p className="mt-2 text-sm text-zinc-400">
              Bu islem tenanti yayindan kaldirir. Veriler silinmez ancak tenant subdomaini artik calismaz.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteConfirmOpen(false)}
                className="rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
              >
                Iptal
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={saving}
                className="rounded border border-red-500/50 px-3 py-2 text-sm font-semibold text-red-200 hover:bg-red-500/10 disabled:opacity-60"
              >
                {saving ? "Isaretleniyor..." : "Silindi Olarak Isaretle"}
              </button>
            </div>
          </div>
        </div>
      )}

      {hardDeleteConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-xl border border-red-500/50 bg-zinc-900 p-4">
            <h3 className="text-base font-semibold text-red-100">Tenant Kalici Olarak Sil</h3>
            <p className="mt-2 text-sm text-zinc-300">
              Bu islem tenanti ve bu tenanta bagli admin, kullanici, randevu, ayar, log ve WhatsApp kayitlarini
              database kaydindan tamamen siler. Bu islem geri alinamaz.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setHardDeleteConfirmOpen(false)}
                className="rounded border border-zinc-700 px-3 py-2 text-sm text-zinc-200 hover:bg-zinc-800"
              >
                Iptal
              </button>
              <button
                type="button"
                onClick={handleHardDelete}
                disabled={saving}
                className="rounded bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-60"
              >
                {saving ? "Siliniyor..." : "Kalici Olarak Sil"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
