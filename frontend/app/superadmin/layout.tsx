/**
 * app/superadmin/layout.tsx - Super admin alaninin ortak layout'u.
 */

export default function SuperAdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <div className="min-h-[100dvh] bg-zinc-950 text-zinc-100">{children}</div>
}
