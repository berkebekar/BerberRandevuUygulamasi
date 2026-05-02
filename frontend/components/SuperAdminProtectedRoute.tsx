/**
 * components/SuperAdminProtectedRoute.tsx - Super admin route guard (server).
 */

import { cookies } from "next/headers"
import { redirect } from "next/navigation"

import { validateSuperAdminSession } from "@/lib/superadmin-api"

type Props = {
  children: React.ReactNode
}

export default async function SuperAdminProtectedRoute({ children }: Props) {
  const cookieStore = cookies()
  const hasSessionCookie = cookieStore.has("superadmin_session")

  if (!hasSessionCookie) {
    redirect("/superadmin/login")
  }

  const isSessionValid = await validateSuperAdminSession(cookieStore.toString())
  if (!isSessionValid) {
    redirect("/superadmin/login")
  }

  return <>{children}</>
}
