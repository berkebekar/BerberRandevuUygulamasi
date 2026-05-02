import type { SuperAdminTenantSummary, UserStatus } from "./types"

export function formatDateTime(value: string | null): string {
  if (!value) return "-"
  return new Date(value).toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Istanbul",
  })
}

const STATUS_LABELS: Record<UserStatus, string> = {
  active: "Aktif",
  blocked: "Engelli",
  deleted: "Silinmis",
}

const STATUS_BADGES: Record<UserStatus, string> = {
  active: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  blocked: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  deleted: "border-red-500/40 bg-red-500/10 text-red-300",
}

export function getStatusLabel(status: UserStatus): string {
  return STATUS_LABELS[status] ?? status
}

export function getStatusBadgeClass(status: UserStatus): string {
  return STATUS_BADGES[status] ?? "border-zinc-700 bg-zinc-800 text-zinc-300"
}

export function formatUserName(firstName: string, lastName: string): string {
  return `${firstName} ${lastName}`.trim()
}

export function buildTenantUserUrl(tenant: SuperAdminTenantSummary): string {
  if (typeof window === "undefined") {
    return "/"
  }
  const current = new URL(window.location.href)
  const [hostnameOnly] = current.host.split(":")
  const port = current.port ? `:${current.port}` : ""
  const parts = hostnameOnly.split(".")
  const firstPart = parts[0] ?? ""

  let targetHost: string
  if (hostnameOnly === "localhost" || parts.length === 1) {
    targetHost = `${tenant.subdomain}.localhost${port}`
  } else {
    parts[0] = tenant.subdomain
    if (firstPart === "tenantadmin" && parts.length >= 2) {
      targetHost = `${tenant.subdomain}.${parts.slice(1).join(".")}${port}`
    } else {
      targetHost = `${parts.join(".")}${port}`
    }
  }

  return `${current.protocol}//${targetHost}/`
}
