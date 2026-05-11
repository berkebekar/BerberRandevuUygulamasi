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

function normalizeConfiguredDomain(value: string | undefined): string {
  return (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .split("/")[0]
    .split(":")[0]
}

function resolveAppDomain(currentHostname: string): string {
  const configuredDomain = normalizeConfiguredDomain(process.env.NEXT_PUBLIC_APP_DOMAIN)

  if (configuredDomain) {
    return configuredDomain.startsWith("www.") ? configuredDomain.slice(4) : configuredDomain
  }

  if (currentHostname.startsWith("superadmin.")) {
    return currentHostname.slice("superadmin.".length)
  }

  if (currentHostname === "bbsoft.com.tr" || currentHostname.endsWith(".bbsoft.com.tr")) {
    return "bbsoft.com.tr"
  }

  if (currentHostname.startsWith("www.")) {
    return currentHostname.slice(4)
  }

  return currentHostname
}

export function buildTenantUserUrl(tenant: SuperAdminTenantSummary): string {
  if (typeof window === "undefined") {
    return "/"
  }
  const current = new URL(window.location.href)
  const [hostnameOnly] = current.host.split(":")
  const port = current.port ? `:${current.port}` : ""

  let targetHost: string
  if (hostnameOnly === "localhost" || hostnameOnly === "127.0.0.1") {
    targetHost = `${tenant.subdomain}.localhost${port}`
  } else {
    targetHost = `${tenant.subdomain}.${resolveAppDomain(hostnameOnly)}`
  }

  return `${current.protocol}//${targetHost}/`
}
