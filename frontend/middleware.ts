import type { NextRequest } from "next/server"
import { NextResponse } from "next/server"

function normalizeHost(request: NextRequest): string {
  const forwarded = request.headers.get("x-forwarded-host")
  const host = (forwarded ?? request.headers.get("host") ?? "").split(",")[0].trim().toLowerCase()
  return host.split(":")[0]
}

function isSuperAdminHost(host: string): boolean {
  const superAdminSubdomain = (process.env.NEXT_PUBLIC_SUPERADMIN_SUBDOMAIN ?? "tenantadmin").toLowerCase()
  return host === superAdminSubdomain || host.startsWith(`${superAdminSubdomain}.`)
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const host = normalizeHost(request)

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set("x-tenant-host", host)

  if (!isSuperAdminHost(host)) {
    return NextResponse.next({ request: { headers: requestHeaders } })
  }

  if (pathname.startsWith("/api/") || pathname.startsWith("/_next/")) {
    return NextResponse.next({ request: { headers: requestHeaders } })
  }

  if (pathname === "/") {
    return NextResponse.redirect(new URL("/superadmin", request.url))
  }

  if (!pathname.startsWith("/superadmin")) {
    return NextResponse.redirect(new URL(`/superadmin${pathname}`, request.url))
  }

  return NextResponse.next({ request: { headers: requestHeaders } })
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
}
