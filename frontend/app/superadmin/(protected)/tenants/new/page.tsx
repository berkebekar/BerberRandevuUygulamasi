"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"

import { SuperAdminApiError, superAdminGet, superAdminPost } from "@/lib/superadmin-api"

import type { TenantCreateRequest, TenantDomainSyncResponse, TenantListResponse } from "../types"
import { isSubdomainValid } from "../utils"

const TR_PHONE_REGEX = /^\+90\d{10}$/

export default function SuperAdminNewTenantPage() {
  const router = useRouter()

  const [subdomain, setSubdomain] = useState("")
  const [name, setName] = useState("")
  const [address, setAddress] = useState("")
  const [adminFirstName, setAdminFirstName] = useState("")
  const [adminLastName, setAdminLastName] = useState("")
  const [adminPhone, setAdminPhone] = useState("")
  const [adminEmail, setAdminEmail] = useState("")

  const [workStartTime, setWorkStartTime] = useState("09:00")
  const [workEndTime, setWorkEndTime] = useState("18:00")
  const [slotDurationMinutes, setSlotDurationMinutes] = useState(30)
  const [weeklyClosedDays, setWeeklyClosedDays] = useState<number[]>([6])

  const [checkingSubdomain, setCheckingSubdomain] = useState(false)
  const [subdomainAvailable, setSubdomainAvailable] = useState<boolean | null>(null)
  const [subdomainMessage, setSubdomainMessage] = useState("")

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  const normalizedSubdomain = useMemo(() => subdomain.trim().toLowerCase(), [subdomain])
  const canCheckSubdomain = normalizedSubdomain.length >= 3 && isSubdomainValid(normalizedSubdomain)

  useEffect(() => {
    if (!normalizedSubdomain) {
      setSubdomainAvailable(null)
      setSubdomainMessage("")
      return
    }

    if (!canCheckSubdomain) {
      setSubdomainAvailable(false)
      setSubdomainMessage("Subdomain sadece kucuk harf, rakam ve '-' icerebilir.")
      return
    }

    const timeoutId = window.setTimeout(async () => {
      setCheckingSubdomain(true)
      try {
        const result = await superAdminGet<TenantListResponse>(
          `/api/v1/superadmin/tenants?page=1&page_size=20&search=${encodeURIComponent(normalizedSubdomain)}`
        )
        const exactExists = result.items.some((item) => item.subdomain.toLowerCase() === normalizedSubdomain)
        if (exactExists) {
          setSubdomainAvailable(false)
          setSubdomainMessage("Bu subdomain zaten kullanimda.")
        } else {
          setSubdomainAvailable(true)
          setSubdomainMessage("Subdomain musait.")
        }
      } catch {
        setSubdomainAvailable(null)
        setSubdomainMessage("Subdomain kontrolu su an yapilamiyor.")
      } finally {
        setCheckingSubdomain(false)
      }
    }, 450)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [normalizedSubdomain, canCheckSubdomain])

  function toggleClosedDay(day: number) {
    setWeeklyClosedDays((prev) => {
      if (prev.includes(day)) {
        return prev.filter((d) => d !== day)
      }
      return [...prev, day].sort((a, b) => a - b)
    })
  }

  function validateForm(): string | null {
    if (!canCheckSubdomain) return "Gecerli bir subdomain girin."
    if (subdomainAvailable === false) return "Subdomain musait degil."
    if (name.trim().length < 2) return "Isletme adi en az 2 karakter olmali."
    if (address.trim().length < 5) return "Adres en az 5 karakter olmali."
    if (adminFirstName.trim().length < 2 || adminLastName.trim().length < 2) return "Admin ad soyad bilgisi zorunlu."
    if (!TR_PHONE_REGEX.test(adminPhone.trim())) return "Admin telefon +90XXXXXXXXXX formatinda olmali."
    if (!adminEmail.includes("@")) return "Gecerli admin email girin."
    if (slotDurationMinutes < 5 || slotDurationMinutes > 180) return "Slot suresi 5-180 arasinda olmali."
    return null
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError("")
    setSuccess("")

    const validationError = validateForm()
    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)
    try {
      const payload: TenantCreateRequest = {
        subdomain: normalizedSubdomain,
        name: name.trim(),
        address: address.trim(),
        admin_first_name: adminFirstName.trim(),
        admin_last_name: adminLastName.trim(),
        admin_phone: adminPhone.trim(),
        admin_email: adminEmail.trim(),
        defaults: {
          work_start_time: workStartTime,
          work_end_time: workEndTime,
          slot_duration_minutes: slotDurationMinutes,
          weekly_closed_days: weeklyClosedDays,
        },
      }
      const response = await superAdminPost<{ tenant: { id: string }; domain_sync?: TenantDomainSyncResponse | null }>(
        "/api/v1/superadmin/tenants",
        payload
      )
      const sync = response.domain_sync
      if (!sync) {
        setError("Tenant olusturuldu ancak domain sync sonucu alinamadi. Tenant detayina gitmeden once Coolify ayarlarini kontrol edin.")
        return
      }
      if (!sync.enabled) {
        setError(`Tenant olusturuldu ancak Coolify otomasyonu kapali veya eksik: ${sync.reason ?? "ayar eksik"}.`)
        return
      }
      if (sync.error) {
        setError(`Tenant olusturuldu ancak Coolify domain sync basarisiz: ${sync.error}`)
        return
      }
      if (sync.deploy_requested) {
        setSuccess("Tenant basariyla olusturuldu. Domain eklendi ve deploy istegi gonderildi.")
      } else {
        setSuccess("Tenant basariyla olusturuldu. Domain eklendi.")
      }
      window.setTimeout(() => router.push(`/superadmin/tenants/${response.tenant.id}`), 2500)
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) setError(err.message)
      else if (err instanceof Error) setError(err.message)
      else setError("Tenant olusturulamadi.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <Link href="/superadmin/tenants" className="text-xs text-zinc-400 hover:text-zinc-200">
          ← Tenant listesine don
        </Link>
        <h1 className="mt-2 text-xl font-bold text-zinc-100">Yeni Tenant</h1>
        <p className="mt-1 text-sm text-zinc-400">Tenant + admin kaydi olustur ve varsayilan ayarlari belirle.</p>
      </div>

      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}
      {success && (
        <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">
          {success}
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/70 p-4">
        <section className="grid gap-3 md:grid-cols-2">
          <div className="md:col-span-2">
            <label className="mb-1 block text-sm font-medium text-zinc-300">Subdomain</label>
            <input
              value={subdomain}
              onChange={(event) => setSubdomain(event.target.value.toLowerCase())}
              placeholder="ornek: acme"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
            <p className="mt-1 text-xs text-zinc-400">
              {checkingSubdomain ? "Kontrol ediliyor..." : subdomainMessage || "Subdomain en az 3 karakter olmalidir."}
            </p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Isletme Adi</label>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Adres</label>
            <textarea
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              rows={3}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Admin Ad</label>
            <input
              value={adminFirstName}
              onChange={(event) => setAdminFirstName(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Admin Soyad</label>
            <input
              value={adminLastName}
              onChange={(event) => setAdminLastName(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Admin Telefon</label>
            <input
              value={adminPhone}
              onChange={(event) => setAdminPhone(event.target.value)}
              placeholder="+905551112233"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Admin Email</label>
            <input
              type="email"
              value={adminEmail}
              onChange={(event) => setAdminEmail(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Calisma Baslangic</label>
            <input
              type="time"
              value={workStartTime}
              onChange={(event) => setWorkStartTime(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Calisma Bitis</label>
            <input
              type="time"
              value={workEndTime}
              onChange={(event) => setWorkEndTime(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-zinc-300">Slot Dakika</label>
            <input
              type="number"
              min={5}
              max={180}
              value={slotDurationMinutes}
              onChange={(event) => setSlotDurationMinutes(Number(event.target.value))}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none"
            />
          </div>
        </section>

        <section>
          <p className="mb-2 text-sm font-medium text-zinc-300">Haftalik Kapali Gunler</p>
          <div className="flex flex-wrap gap-2">
            {["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"].map((label, idx) => {
              const selected = weeklyClosedDays.includes(idx)
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => toggleClosedDay(idx)}
                  className={`rounded-lg border px-3 py-1.5 text-xs ${
                    selected ? "border-zinc-100 bg-zinc-100 text-zinc-900" : "border-zinc-700 text-zinc-200 hover:bg-zinc-800"
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </section>

        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-zinc-100 px-4 py-2 text-sm font-semibold text-zinc-900 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Kaydediliyor..." : "Tenant Olustur"}
        </button>
      </form>
    </div>
  )
}
