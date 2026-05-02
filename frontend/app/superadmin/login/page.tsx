"use client"

import { useMemo, useState } from "react"

import { SuperAdminApiError, superAdminPost } from "@/lib/superadmin-api"

type LoginResponse = {
  message: string
}

export default function SuperAdminLoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const isFormValid = useMemo(() => username.trim().length >= 3 && password.length >= 6, [username, password])

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!isFormValid) {
      setError("Kullanici adi veya sifre gecersiz.")
      return
    }

    setError("")
    setIsLoading(true)
    try {
      await superAdminPost<LoginResponse>("/api/v1/superadmin/auth/login", {
        username: username.trim(),
        password,
      })
      // Cookie set kontrolu server tarafinda protected route'da yapilir.
      window.location.assign("/superadmin")
    } catch (err: unknown) {
      if (err instanceof SuperAdminApiError) {
        setError(err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError("Giris yapilamadi.")
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center px-4 py-8">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900/80 p-6 shadow-2xl shadow-black/25">
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">Platform</p>
          <h1 className="mt-2 text-2xl font-bold text-zinc-100">Super Admin Girisi</h1>
          <p className="mt-1 text-sm text-zinc-400">Kullanici adi ve sifre ile giris yapin.</p>
        </div>

        <form className="space-y-4" onSubmit={handleLogin}>
          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium text-zinc-300">
              Kullanici Adi
            </label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              disabled={isLoading}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 outline-none transition focus:border-zinc-500"
              placeholder="ornek: owner"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium text-zinc-300">
              Sifre
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isLoading}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 outline-none transition focus:border-zinc-500"
              placeholder="********"
            />
          </div>

          {error && <p className="rounded-md bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>}

          <button
            type="submit"
            disabled={isLoading || !isFormValid}
            className="w-full rounded-lg bg-zinc-100 px-3 py-2.5 text-sm font-semibold text-zinc-900 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Giris yapiliyor..." : "Giris Yap"}
          </button>
        </form>
      </div>
    </div>
  )
}
