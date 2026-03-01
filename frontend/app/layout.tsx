/**
 * layout.tsx â€” UygulamanÄ±n kÃ¶k layout'u.
 * TÃ¼m sayfalar bu layout iÃ§inde render edilir.
 * globals.css burada import edilerek Tailwind stilleri uygulamaya yÃ¼klenir.
 */

import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "Berber Randevu",
  description: "Tek berber randevu sistemi",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="tr">
      {/* antialiased: font kenarlarÄ±nÄ± yumuÅŸatÄ±r, min-h-screen: sayfa en az tam ekran yÃ¼ksekliÄŸinde */}
      <body className="antialiased min-h-screen bg-zinc-950">
        {children}
      </body>
    </html>
  )
}

