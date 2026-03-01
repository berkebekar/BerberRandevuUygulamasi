/**
 * app/(customer)/layout.tsx â€” MÃ¼ÅŸteri sayfalarÄ± iÃ§in ortak layout.
 *
 * /auth haricindeki tÃ¼m mÃ¼ÅŸteri sayfalarÄ± iÃ§in auth kontrolÃ¼ burada yapÄ±lÄ±r.
 * Server Component olarak Ã§alÄ±ÅŸÄ±r:
 *   - cookies() ile user_session cookie'sini okur
 *   - Cookie yoksa /auth'a yÃ¶nlendirir
 *   - Bu kontrol sunucu tarafÄ±nda Ã§alÄ±ÅŸÄ±r, istemciye hiÃ§ gÃ¶nderilmez
 */

import { cookies } from "next/headers"
import { redirect } from "next/navigation"

export default function CustomerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // next/headers'dan cookie'leri oku â€” bu sadece Server Component'ta Ã§alÄ±ÅŸÄ±r
  const cookieStore = cookies()

  // user_session cookie'si yoksa kullanÄ±cÄ± giriÅŸ yapmamÄ±ÅŸ demektir
  // /auth sayfasÄ±na yÃ¶nlendir â€” /auth sayfasÄ± bu layout iÃ§inde OLMAZ
  // Not: /auth kendi route'u olduÄŸu iÃ§in bu layout'a dahil deÄŸil,
  //       bu nedenle sonsuz dÃ¶ngÃ¼ oluÅŸmaz
  const hasSession = cookieStore.has("user_session")

  if (!hasSession) {
    redirect("/auth")
  }

  return (
    // Mobil-first: maksimum geniÅŸlik 480px, ortalanmÄ±ÅŸ
    <div className="min-h-screen bg-zinc-950">
      <div className="max-w-lg mx-auto">
        {children}
      </div>
    </div>
  )
}

