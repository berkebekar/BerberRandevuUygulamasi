import { expect, test } from "@playwright/test"

import { getSeedData, loginSuperAdmin, logoutSuperAdmin } from "./helpers/superadmin"

test("tenant create flow", async ({ request }) => {
  const seed = await getSeedData(request)
  await loginSuperAdmin(request, seed.superadmin_username, seed.superadmin_password)

  const suffix = Date.now()
  const subdomain = `e2e-${suffix}`

  const createResponse = await request.post("/api/v1/superadmin/tenants", {
    data: {
      subdomain,
      name: `E2E Tenant ${suffix}`,
      admin_first_name: "E2E",
      admin_last_name: "Admin",
      admin_phone: `+90555${String(suffix).slice(-7)}`,
      admin_email: `e2e.${suffix}@example.com`,
      defaults: {
        work_start_time: "09:00",
        work_end_time: "18:00",
        slot_duration_minutes: 30,
        weekly_closed_days: [6],
      },
    },
  })

  expect(createResponse.status()).toBe(201)
  const createPayload = await createResponse.json()
  expect(createPayload.tenant.subdomain).toBe(subdomain)

  const listResponse = await request.get(`/api/v1/superadmin/tenants?page=1&page_size=20&search=${subdomain}`)
  await expect(listResponse).toBeOK()
  const listPayload = await listResponse.json()
  expect(listPayload.items.some((item: { subdomain: string }) => item.subdomain === subdomain)).toBeTruthy()

  await logoutSuperAdmin(request)
})
