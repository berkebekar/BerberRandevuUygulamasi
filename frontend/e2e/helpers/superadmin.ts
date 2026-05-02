import { APIRequestContext, expect } from "@playwright/test"

type SeedPayload = {
  superadmin_username: string
  superadmin_password: string
  seeded_tenant_id: string
  seeded_tenant_subdomain: string
  seeded_user_id: string
  seeded_user_phone: string
}

export async function getSeedData(request: APIRequestContext): Promise<SeedPayload> {
  const response = await request.get("/api/v1/ping")
  await expect(response).toBeOK()

  const seeded = process.env.E2E_SEED_JSON
  if (!seeded) {
    throw new Error("E2E_SEED_JSON env zorunlu. Once `npm run e2e:seed` calistirin.")
  }
  return JSON.parse(seeded) as SeedPayload
}

export async function loginSuperAdmin(request: APIRequestContext, username: string, password: string): Promise<void> {
  const response = await request.post("/api/v1/superadmin/auth/login", {
    data: { username, password },
  })
  await expect(response).toBeOK()
}

export async function logoutSuperAdmin(request: APIRequestContext): Promise<void> {
  await request.post("/api/v1/superadmin/auth/logout", {
    data: {},
  })
}
