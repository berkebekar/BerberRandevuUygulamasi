/**
 * app/(customer)/layout.tsx - Musteri sayfalari icin ortak layout.
 */

import { cookies } from "next/headers"
import { redirect } from "next/navigation"

import CustomerImpersonationBanner from "@/components/CustomerImpersonationBanner"

function isUserImpersonationToken(token: string | undefined): boolean {
  if (!token) return false
  try {
    const parts = token.split(".")
    if (parts.length !== 3) return false
    const payloadRaw = parts[1].replace(/-/g, "+").replace(/_/g, "/")
    const padded = payloadRaw.padEnd(Math.ceil(payloadRaw.length / 4) * 4, "=")
    const payloadJson = Buffer.from(padded, "base64").toString("utf8")
    const payload = JSON.parse(payloadJson) as { imp?: unknown; role?: unknown }
    return payload.imp === true && payload.role === "user"
  } catch {
    return false
  }
}

export default function CustomerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const cookieStore = cookies()
  const hasSession = cookieStore.has("user_session")

  if (!hasSession) {
    redirect("/auth")
  }

  const userSession = cookieStore.get("user_session")?.value
  const isImpersonated = isUserImpersonationToken(userSession)

  return (
    <div className="min-h-screen bg-zinc-950">
      {isImpersonated && <CustomerImpersonationBanner />}
      <div className="max-w-lg mx-auto">{children}</div>
    </div>
  )
}
