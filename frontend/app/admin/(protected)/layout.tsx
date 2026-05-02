/**
 * app/admin/(protected)/layout.tsx â€” Admin sayfalari icin route korumasi.
 *
 * admin_session cookie yoksa /auth sayfasina yonlendirir.
 * Bu kontrol server component'ta calisir, client'a veri sizmadan yapilir.
 */

import { cookies } from "next/headers"
import { redirect } from "next/navigation"

import AdminImpersonationBanner from "@/components/AdminImpersonationBanner"

function isAdminImpersonationToken(token: string | undefined): boolean {
  if (!token) return false
  try {
    const parts = token.split(".")
    if (parts.length !== 3) return false
    const payloadRaw = parts[1].replace(/-/g, "+").replace(/_/g, "/")
    const padded = payloadRaw.padEnd(Math.ceil(payloadRaw.length / 4) * 4, "=")
    const payloadJson = Buffer.from(padded, "base64").toString("utf8")
    const payload = JSON.parse(payloadJson) as { imp?: unknown; role?: unknown }
    return payload.imp === true && payload.role === "admin"
  } catch {
    return false
  }
}

export default function AdminProtectedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // HTTP-only cookie'yi server tarafinda oku
  const cookieStore = cookies()

  // admin_session yoksa auth sayfasina yonlendir
  const hasSession = cookieStore.has("admin_session")
  // Session yoksa auth sayfasina yonlendir
  if (!hasSession) {
    redirect("/auth")
  }
  const adminSession = cookieStore.get("admin_session")?.value
  const isImpersonated = isAdminImpersonationToken(adminSession)

  return (
    // Mobil-first container
    <div className="min-h-screen bg-zinc-950">
      {isImpersonated && <AdminImpersonationBanner />}
      <div className="max-w-lg mx-auto">
        {children}
      </div>
    </div>
  )
}

