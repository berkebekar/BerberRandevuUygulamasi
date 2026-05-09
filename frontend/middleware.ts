import type { NextRequest } from "next/server"
import { NextResponse } from "next/server"

function normalizeHost(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-host")
  const host = (forwarded ?? request.headers.get("host") ?? "").split(",")[0].trim().toLowerCase()
  return host.split(":")[0]
}

function normalizeConfiguredHost(value: string | undefined): string {
  return (value ?? "")
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .split("/")[0]
    .split(":")[0]
}

const RESERVED_SUBDOMAINS = new Set(["api", "admin", "mail", "smtp", "pop", "ftp"])

function configuredPlatformHost(): string {
  return (
    normalizeConfiguredHost(process.env.NEXT_PUBLIC_SUPERADMIN_HOST) ||
    normalizeConfiguredHost(process.env.NEXT_PUBLIC_APP_DOMAIN) ||
    "bbsoft.com.tr"
  )
}

function isPlatformHost(host: string): boolean {
  const configuredHost = configuredPlatformHost()
  const wwwHost = configuredHost.startsWith("www.") ? configuredHost : `www.${configuredHost}`

  if (host === configuredHost || host === wwwHost) {
    return true
  }

  return process.env.NODE_ENV !== "production" && (host === "localhost" || host === "127.0.0.1")
}

function isReservedSubdomain(host: string): boolean {
  const configuredHost = configuredPlatformHost()
  if (!host.endsWith(`.${configuredHost}`)) {
    return false
  }

  const subdomain = host.slice(0, -(configuredHost.length + 1))
  return RESERVED_SUBDOMAINS.has(subdomain)
}

function isCustomerRoute(pathname: string): boolean {
  return (
    pathname === "/auth" ||
    pathname.startsWith("/auth/") ||
    pathname === "/admin" ||
    pathname.startsWith("/admin/") ||
    pathname === "/settings" ||
    pathname.startsWith("/settings/") ||
    pathname === "/confirm" ||
    pathname.startsWith("/confirm/")
  )
}

function isCustomerApiRoute(pathname: string): boolean {
  return pathname === "/api/v1" || (pathname.startsWith("/api/v1/") && !isSuperAdminApiRoute(pathname))
}

function isSuperAdminHost(host: string): boolean {
  const configuredHost =
    normalizeConfiguredHost(process.env.NEXT_PUBLIC_SUPERADMIN_HOST) ||
    normalizeConfiguredHost(process.env.NEXT_PUBLIC_APP_DOMAIN) ||
    "bbsoft.com.tr"

  if (host === configuredHost) {
    return true
  }

  return process.env.NODE_ENV !== "production" && (host === "localhost" || host === "127.0.0.1")
}

function isSuperAdminRoute(pathname: string): boolean {
  return pathname === "/superadmin" || pathname.startsWith("/superadmin/")
}

function isSuperAdminApiRoute(pathname: string): boolean {
  return pathname === "/api/v1/superadmin" || pathname.startsWith("/api/v1/superadmin/")
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const host = normalizeHost(request)

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set("x-tenant-host", host)

  if (isReservedSubdomain(host)) {
    return new NextResponse("Not Found", { status: 404 })
  }

  if (isPlatformHost(host)) {
    if (pathname === "/") {
      const url = request.nextUrl.clone()
      url.pathname = "/platform"
      return NextResponse.rewrite(url, { request: { headers: requestHeaders } })
    }

    if (isCustomerRoute(pathname) || isCustomerApiRoute(pathname)) {
      return new NextResponse("Not Found", { status: 404 })
    }

    return NextResponse.next({ request: { headers: requestHeaders } })
  }

  if (!isSuperAdminHost(host)) {
    if (isSuperAdminRoute(pathname) || isSuperAdminApiRoute(pathname)) {
      return new NextResponse("Not Found", { status: 404 })
    }

    if (pathname === "/platform" || pathname.startsWith("/platform/")) {
      return new NextResponse("Not Found", { status: 404 })
    }

    return NextResponse.next({ request: { headers: requestHeaders } })
  }

  return NextResponse.next({ request: { headers: requestHeaders } })
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
}
