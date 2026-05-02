import { spawnSync } from "node:child_process"
import path from "node:path"
import process from "node:process"

const root = process.cwd()
const backendDir = path.resolve(root, "..", "backend")
const pythonExe = process.platform === "win32"
  ? path.join(backendDir, ".venv", "Scripts", "python.exe")
  : path.join(backendDir, ".venv", "bin", "python")

const seed = spawnSync(pythonExe, ["scripts/seed_e2e_data.py"], {
  cwd: backendDir,
  encoding: "utf8",
  env: process.env,
})

if (seed.error) {
  process.stderr.write(`${seed.error.message}\n`)
  process.exit(1)
}

if (seed.status !== 0) {
  process.stderr.write(seed.stderr || "E2E seed script failed.\n")
  if (seed.stdout) {
    process.stderr.write(seed.stdout)
  }
  process.exit(seed.status ?? 1)
}

process.stdout.write((seed.stdout || "").trim() + "\n")
