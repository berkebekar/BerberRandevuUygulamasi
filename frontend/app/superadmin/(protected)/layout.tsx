import Link from "next/link"

import SuperAdminLogoutButton from "@/components/SuperAdminLogoutButton"
import SuperAdminProtectedRoute from "@/components/SuperAdminProtectedRoute"

const MENU_ITEMS: Array<{ href: string; label: string }> = [
  { href: "/superadmin", label: "Dashboard" },
  { href: "/superadmin/tenants", label: "Tenants" },
  { href: "/superadmin/users", label: "Users" },
  { href: "/superadmin/whatsapp", label: "WhatsApp Bot" },
  { href: "/superadmin/monitoring", label: "Monitoring" },
  { href: "/superadmin/logs/errors", label: "Error Logs" },
  { href: "/superadmin/logs/activities", label: "Activity Logs" },
]

export default function SuperAdminProtectedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SuperAdminProtectedRoute>
      <div className="grid min-h-[100dvh] grid-cols-1 md:grid-cols-[250px_1fr]">
        <aside className="border-b border-zinc-800 bg-zinc-900/80 px-4 py-5 md:border-b-0 md:border-r">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-400">Super Admin</p>
          <nav className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-1">
            {MENU_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg border border-zinc-800 px-3 py-2 text-sm font-medium text-zinc-200 transition hover:border-zinc-600 hover:bg-zinc-800/50"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        <main className="flex min-h-0 flex-col">
          <header className="flex items-center justify-between border-b border-zinc-800 bg-zinc-900/60 px-4 py-3">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-zinc-500">Platform Console</p>
              <p className="text-sm font-semibold text-zinc-100">Super Admin</p>
            </div>
            <SuperAdminLogoutButton />
          </header>
          <section className="flex-1 px-4 py-5">{children}</section>
        </main>
      </div>
    </SuperAdminProtectedRoute>
  )
}
