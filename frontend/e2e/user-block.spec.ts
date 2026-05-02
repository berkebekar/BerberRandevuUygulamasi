import { expect, test } from "@playwright/test"

import { getSeedData, loginSuperAdmin, logoutSuperAdmin } from "./helpers/superadmin"

test("user block/unblock flow", async ({ request }) => {
  const seed = await getSeedData(request)
  await loginSuperAdmin(request, seed.superadmin_username, seed.superadmin_password)

  const blockResponse = await request.put(`/api/v1/superadmin/users/${seed.seeded_user_id}/block`, {
    data: { reason: "e2e_policy_test" },
  })
  await expect(blockResponse).toBeOK()
  const blocked = await blockResponse.json()
  expect(blocked.status).toBe("blocked")

  const detailBlocked = await request.get(`/api/v1/superadmin/users/${seed.seeded_user_id}?booking_page=1&booking_page_size=10`)
  await expect(detailBlocked).toBeOK()
  const detailBlockedPayload = await detailBlocked.json()
  expect(detailBlockedPayload.status).toBe("blocked")

  const unblockResponse = await request.put(`/api/v1/superadmin/users/${seed.seeded_user_id}/unblock`, {
    data: {},
  })
  await expect(unblockResponse).toBeOK()
  const unblocked = await unblockResponse.json()
  expect(unblocked.status).toBe("active")

  await logoutSuperAdmin(request)
})
