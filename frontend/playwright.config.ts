import { defineConfig } from "@playwright/test"

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  workers: 1,
  expect: {
    timeout: 5_000,
  },
  fullyParallel: false,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BACKEND_BASE_URL ?? "http://localhost:8000",
    extraHTTPHeaders: {
      Host: process.env.E2E_BACKEND_HOST ?? "localhost:8000",
      "Content-Type": "application/json",
    },
  },
})
