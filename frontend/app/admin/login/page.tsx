/**
 * app/admin/login/page.tsx — Admin giris sayfasi.
 *
 * Iki sekme:
 * - SMS ile Giris (telefon + OTP)
 * - Sifre ile Giris (email + sifre)
 */

"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { PhoneInput, OTPInput } from "@/components"
import { apiPost } from "@/lib/api"

type Tab = "sms" | "password"
type Step = "phone" | "otp"
const TR_PHONE_REGEX = /^\+90\d{10}$/

export default function AdminLoginPage() {
  const router = useRouter()

  // Aktif sekme: sms veya password
  const [tab, setTab] = useState<Tab>("sms")

  // SMS akisi icin adim
  const [step, setStep] = useState<Step>("phone")

  // Ortak form alanlari
  const [phone, setPhone] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  // UI state
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [countdown, setCountdown] = useState(0)

  // OTP tekrar gonderme icin geri sayim
  useEffect(() => {
    // Geri sayim sifira ulastiysa timer kurma
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  /**
   * SMS adim 1: telefon numarasina OTP gonder.
   */
  async function handleSendOtp() {
    // Telefon numarasi eksik veya kisa ise erken cik
    if (!TR_PHONE_REGEX.test(phone)) {
      setError("Lutfen gecerli bir telefon numarasi girin.")
      return
    }

    setError("")
    setIsLoading(true)
    try {
      await apiPost("/api/v1/auth/admin/send-otp", { phone })
      setStep("otp")
      setCountdown(60)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kod gonderilemedi.")
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * SMS adim 2: OTP dogrula ve admin session cookie set edilsin.
   */
  async function handleVerifyOtp(code: string) {
    setError("")
    setIsLoading(true)
    try {
      await apiPost("/api/v1/auth/admin/verify-otp", { phone, code })
      router.push("/admin")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kod dogrulanamadi.")
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Sifre ile giris.
   */
  async function handleLoginPassword() {
    // Email veya sifre bos ise erken cik
    if (!email.trim() || !password.trim()) {
      setError("Lutfen email ve sifre girin.")
      return
    }

    setError("")
    setIsLoading(true)
    try {
      await apiPost("/api/v1/auth/admin/login/password", {
        email: email.trim(),
        password,
      })
      router.push("/admin")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Giris basarisiz.")
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * SMS sekmesine gecince formu temizle.
   */
  function switchToSms() {
    setTab("sms")
    setError("")
    setStep("phone")
    setCountdown(0)
  }

  /**
   * Sifre sekmesine gecince formu temizle.
   */
  function switchToPassword() {
    setTab("password")
    setError("")
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col justify-center px-4 py-12">
      <div className="w-full max-w-sm mx-auto">
        {/* Baslik */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">✂</div>
          <h1 className="text-2xl font-bold text-zinc-100">Admin Giris</h1>
          <p className="text-zinc-400 text-sm mt-1">
            Berber paneline giris yapin
          </p>
        </div>

        {/* Sekmeler */}
        <div className="bg-zinc-900 rounded-2xl shadow-sm border border-zinc-800 p-2 mb-4">
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={switchToSms}
              className={`py-2 rounded-xl text-sm font-medium transition-colors ${
                tab === "sms"
                  ? "bg-zinc-100 text-zinc-950"
                  : "bg-zinc-950 text-zinc-400"
              }`}
            >
              SMS ile Giris
            </button>
            <button
              onClick={switchToPassword}
              className={`py-2 rounded-xl text-sm font-medium transition-colors ${
                tab === "password"
                  ? "bg-zinc-100 text-zinc-950"
                  : "bg-zinc-950 text-zinc-400"
              }`}
            >
              Sifre ile Giris
            </button>
          </div>
        </div>

        {/* Form karti */}
        <div className="bg-zinc-900 rounded-2xl shadow-sm border border-zinc-800 p-6">
          {/* SMS tab */}
          {/* SMS sekmesi aktifse SMS formunu goster */}
          {tab === "sms" && (
            <div className="space-y-4">
              {/* Telefon adimi aktifse telefon formunu goster */}
              {step === "phone" && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                      Telefon Numarasi
                    </label>
                    <PhoneInput onChange={setPhone} disabled={isLoading} />
                  </div>

                  {error && (
                    <p className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">
                      {error}
                    </p>
                  )}

                  <button
                    onClick={handleSendOtp}
                    disabled={isLoading || !phone}
                    className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
                  >
                    {isLoading ? "Gonderiliyor..." : "Kod Gonder"}
                  </button>
                </div>
              )}

              {/* OTP adimi aktifse OTP formunu goster */}
              {step === "otp" && (
                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-3 text-center">
                      {phone} numarasina gonderilen kodu girin
                    </label>
                    <OTPInput onComplete={handleVerifyOtp} disabled={isLoading} />
                  </div>

                  {error && (
                    <p className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2 text-center">
                      {error}
                    </p>
                  )}

                  {isLoading && (
                    <p className="text-center text-sm text-zinc-400">
                      Dogrulaniyor...
                    </p>
                  )}

                  {/* Geri sayim aktifse tekrar gonderi kapat */}
                  <div className="text-center">
                    {countdown > 0 ? (
                      <p className="text-sm text-zinc-400">
                        Tekrar gonder ({countdown}s)
                      </p>
                    ) : (
                      <button
                        onClick={handleSendOtp}
                        disabled={isLoading}
                        className="text-sm text-zinc-200 font-medium underline underline-offset-2 disabled:opacity-50"
                      >
                        Kodu tekrar gonder
                      </button>
                    )}
                  </div>

                  <button
                    onClick={() => {
                      setStep("phone")
                      setError("")
                    }}
                    className="w-full text-sm text-zinc-400 hover:text-zinc-300"
                  >
                    ← Numarayi degistir
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Sifre tab */}
          {/* Sifre sekmesi aktifse sifre formunu goster */}
          {tab === "password" && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  placeholder="ornek@mail.com"
                  className="w-full px-3 py-3 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent disabled:bg-zinc-950"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                  Sifre
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  placeholder="••••••••"
                  className="w-full px-3 py-3 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent disabled:bg-zinc-950"
                />
              </div>

              {error && (
                <p className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">
                  {error}
                </p>
              )}

              <button
                onClick={handleLoginPassword}
                disabled={isLoading}
                className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                {isLoading ? "Giris yapiliyor..." : "Giris Yap"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


