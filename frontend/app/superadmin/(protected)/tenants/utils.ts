import type { TenantStatus } from "./types"

const TENANT_STATUS_LABELS: Record<TenantStatus, string> = {
  active: "Aktif",
  inactive: "Pasif",
  deleted: "Silinmis",
}

const TENANT_STATUS_BADGES: Record<TenantStatus, string> = {
  active: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  inactive: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  deleted: "border-red-500/40 bg-red-500/10 text-red-300",
}

export function getTenantStatusLabel(status: TenantStatus): string {
  return TENANT_STATUS_LABELS[status] ?? status
}

export function getTenantStatusBadgeClass(status: TenantStatus): string {
  return TENANT_STATUS_BADGES[status] ?? "border-zinc-700 bg-zinc-800 text-zinc-300"
}

export function formatTenantDate(value: string): string {
  return new Date(value).toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Europe/Istanbul",
  })
}

export function isSubdomainValid(value: string): boolean {
  return /^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$/.test(value)
}

export function buildTenantAdminUrl(subdomain: string): string {
  if (typeof window === "undefined") {
    return "/admin"
  }

  const current = new URL(window.location.href)
  const [hostnameOnly] = current.host.split(":")
  const port = current.port ? `:${current.port}` : ""
  const hostParts = hostnameOnly.split(".")
  const firstPart = hostParts[0] ?? ""

  let targetHost: string
  if (hostnameOnly === "localhost" || hostParts.length === 1) {
    targetHost = `${subdomain}.localhost${port}`
  } else {
    hostParts[0] = subdomain
    if (firstPart === "tenantadmin" && hostParts.length >= 2) {
      targetHost = `${subdomain}.${hostParts.slice(1).join(".")}${port}`
    } else {
      targetHost = `${hostParts.join(".")}${port}`
    }
  }

  return `${current.protocol}//${targetHost}/admin`
}
