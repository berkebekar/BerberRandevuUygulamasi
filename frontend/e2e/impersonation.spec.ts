import { expect, test } from "@playwright/test"

import { getSeedData, loginSuperAdmin, logoutSuperAdmin } from "./helpers/superadmin"

test("impersonation flow (tenant admin + user)", async ({ request }) => {
  const seed = await getSeedData(request)
  await loginSuperAdmin(request, seed.superadmin_username, seed.superadmin_password)

  const tenantImp = await request.post(`/api/v1/superadmin/tenants/${seed.seeded_tenant_id}/impersonate`)
  await expect(tenantImp).toBeOK()
  const tenantImpPayload = await tenantImp.json()
  expect(tenantImpPayload.message).toBe("impersonation_started")

  const exitAdminImp = await request.post("/api/v1/superadmin/impersonate/exit", { data: {} })
  await expect(exitAdminImp).toBeOK()

  const userImp = await request.post(`/api/v1/superadmin/users/${seed.seeded_user_id}/impersonate`)
  await expect(userImp).toBeOK()
  const userImpPayload = await userImp.json()
  expect(userImpPayload.message).toBe("impersonation_started")

  const exitUserImp = await request.post("/api/v1/superadmin/impersonate/exit", { data: {} })
  await expect(exitUserImp).toBeOK()

  await logoutSuperAdmin(request)
})
