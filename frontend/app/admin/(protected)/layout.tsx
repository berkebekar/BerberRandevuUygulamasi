/**
 * app/admin/(protected)/layout.tsx â€” Admin sayfalari icin route korumasi.
 *
 * admin_session cookie yoksa /admin/login sayfasina yonlendirir.
 * Bu kontrol server component'ta calisir, client'a veri sizmadan yapilir.
 */

import { cookies } from "next/headers"
import { redirect } from "next/navigation"

export default function AdminProtectedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // HTTP-only cookie'yi server tarafinda oku
  const cookieStore = cookies()

  // admin_session yoksa login sayfasina yonlendir
  const hasSession = cookieStore.has("admin_session")
  // Session yoksa login sayfasina yonlendir
  if (!hasSession) {
    redirect("/admin/login")
  }

  return (
    // Mobil-first container
    <div className="min-h-screen bg-zinc-950">
      <div className="max-w-lg mx-auto">
        {children}
      </div>
    </div>
  )
}

