import { spawn, spawnSync } from "node:child_process"
import path from "node:path"
import process from "node:process"

const root = process.cwd()
const backendDir = path.resolve(root, "..", "backend")
const pythonExe = process.platform === "win32"
  ? path.join(backendDir, ".venv", "Scripts", "python.exe")
  : path.join(backendDir, ".venv", "bin", "python")

const backendPort = process.env.E2E_BACKEND_PORT ?? "8010"
const backendBaseUrl = `http://127.0.0.1:${backendPort}`
const databaseUrlSync = process.env.E2E_DATABASE_URL_SYNC ?? "postgresql://postgres:postgres@localhost:5432/postgres"

function runCommand(exe, args, cwd, env, label) {
  const result = spawnSync(exe, args, {
    cwd,
    env,
    encoding: "utf8",
  })

  if (result.error) {
    throw new Error(`${label} error: ${result.error.message}`)
  }
  if (result.status !== 0) {
    throw new Error(`${label} failed:\n${result.stderr || result.stdout}`)
  }
  return (result.stdout || "").trim()
}

async function waitForHealth(url, timeoutMs) {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    try {
      const res = await fetch(`${url}/health`)
      if (res.ok) return
    } catch {
      // retry
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  throw new Error("Backend health check timeout")
}

const backendEnv = {
  ...process.env,
  DATABASE_URL_SYNC: databaseUrlSync,
  DATABASE_URL: process.env.E2E_DATABASE_URL ?? "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
}

const backend = spawn(
  pythonExe,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", backendPort],
  {
    cwd: backendDir,
    env: backendEnv,
    stdio: "pipe",
  }
)

backend.stdout.on("data", (chunk) => {
  process.stdout.write(`[backend] ${chunk}`)
})
backend.stderr.on("data", (chunk) => {
  process.stderr.write(`[backend] ${chunk}`)
})

let exitCode = 1

try {
  await waitForHealth(backendBaseUrl, 60_000)

  runCommand(
    process.platform === "win32" ? path.join(backendDir, ".venv", "Scripts", "alembic.exe") : path.join(backendDir, ".venv", "bin", "alembic"),
    ["upgrade", "head"],
    backendDir,
    backendEnv,
    "Alembic upgrade"
  )

  const seedJson = runCommand(pythonExe, ["scripts/seed_e2e_data.py"], backendDir, backendEnv, "E2E seed")
  if (!seedJson) {
    throw new Error("E2E seed returned empty output")
  }

  const playwrightCli = path.join(root, "node_modules", "@playwright", "test", "cli.js")
  const args = process.argv.slice(2)
  const run = spawnSync(process.execPath, [playwrightCli, "test", ...args], {
    cwd: root,
    stdio: "inherit",
    env: {
      ...process.env,
      E2E_SEED_JSON: seedJson,
      E2E_BACKEND_BASE_URL: backendBaseUrl,
      E2E_BACKEND_HOST: `127.0.0.1:${backendPort}`,
    },
  })

  if (run.error) {
    throw new Error(`Playwright run error: ${run.error.message}`)
  }
  exitCode = run.status ?? 1
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`)
  exitCode = 1
} finally {
  if (!backend.killed) {
    backend.kill("SIGTERM")
  }
}

process.exit(exitCode)
