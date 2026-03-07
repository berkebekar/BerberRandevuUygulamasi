/**
 * app/(customer)/auth/page.tsx — Müşteri giriş sayfası.
 *
 * 3 aşamalı form akışı:
 *   1. "phone"    → Telefon numarası gir, "Kod Gönder" butonuna bas
 *   2. "otp"      → 6 haneli SMS kodunu gir (60sn geri sayım, tekrar gönder)
 *   3. "register" → Yeni kullanıcıysa isim ve soyisim gir
 *
 * Başarılı girişte role göre "/" veya "/admin" sayfasına yönlendirir.
 */

"use client"

import { useState, useEffect } from "react"
import { PhoneInput, OTPInput } from "@/components"
import { apiPost } from "@/lib/api"

// Formun hangi aşamada olduğunu temsil eder
type Step = "phone" | "otp" | "register"
const TR_PHONE_REGEX = /^\+90\d{10}$/

export default function AuthPage() {
  // Hangi aşamadayız
  const [step, setStep] = useState<Step>("phone")

  // Form alanları
  const [phone, setPhone] = useState("")
  const [otp, setOtp] = useState("")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [registrationToken, setRegistrationToken] = useState("")

  // Yükleme ve hata durumları
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  // OTP tekrar gönderme için geri sayım (saniye)
  const [countdown, setCountdown] = useState(0)

  // Geri sayım her saniye azalır
  useEffect(() => {
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    // Bileşen unmount olursa timer'ı temizle — bellek sızıntısını önler
    return () => clearTimeout(timer)
  }, [countdown])

  /**
   * Aşama 1: Telefon numarasını backend'e gönder, OTP SMS'i iste.
   */
  async function handleSendOtp() {
    if (!TR_PHONE_REGEX.test(phone)) {
      setError("Lütfen geçerli bir telefon numarası girin.")
      return
    }

    setError("")
    setIsLoading(true)
    try {
      await apiPost("/api/v1/auth/send-otp", { phone })
      // Başarıyla gönderildiyse OTP aşamasına geç
      setStep("otp")
      // 60 saniye geri sayım başlat — rate limit aynı süre
      setCountdown(60)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Bir hata oluştu.")
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Aşama 2: Kullanıcının girdiği OTP kodunu doğrula.
   * Yanıt: { status: "returning_user" | "new_user", registration_token?: string }
   */
  async function handleVerifyOtp(code: string) {
    setOtp(code)
    setError("")
    setIsLoading(true)
    try {
      const res = await apiPost<{ next: "admin" | "user" | "register"; registration_token?: string }>(
        "/api/v1/auth/verify-otp",
        { phone, code }
      )

      if (res.next === "register") {
        // Yeni kullanıcı — registration_token ile isim/soyisim kayıt aşamasına geç
        setRegistrationToken(res.registration_token ?? "")
        setStep("register")
      } else if (res.next === "admin") {
        // Admin oturumu açıldı
        window.location.assign("/admin")
      } else {
        // Cookie set işleminin tüm tarayıcılarda kesinleşmesi için tam sayfa yönlendirme kullan.
        window.location.assign("/")
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kod doğrulanamadı.")
      // Hatalı OTP: alanları sıfırla, tekrar deneme için temizle
      setOtp("")
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Aşama 3 (opsiyonel): Yeni kullanıcı için isim/soyisim kaydını tamamla.
   */
  async function handleRegister() {
    if (!firstName.trim() || !lastName.trim()) {
      setError("Lütfen adınızı ve soyadınızı girin.")
      return
    }

    setError("")
    setIsLoading(true)
    try {
      await apiPost("/api/v1/auth/user/complete-registration", {
        registration_token: registrationToken,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      })
      // Cookie set işleminin tüm tarayıcılarda kesinleşmesi için tam sayfa yönlendirme kullan.
      window.location.assign("/")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kayıt tamamlanamadı.")
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * OTP kodunu tekrar gönder — 60sn dolmadan bu buton disabled
   */
  async function handleResendOtp() {
    if (countdown > 0) return
    setError("")
    setIsLoading(true)
    try {
      await apiPost("/api/v1/auth/send-otp", { phone })
      setCountdown(60)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kod gönderilemedi.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    // Mobilde klavye acildiginda ziplamayi azaltmak icin dikey ortalama yerine ustten hizala.
    <div className="min-h-[100dvh] bg-zinc-950 px-4 py-6 sm:py-10">
      <div className="w-full max-w-sm mx-auto">

        {/* Logo / Başlık */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">✂️</div>
          <h1 className="text-2xl font-bold text-zinc-100">Berber Randevu</h1>
          <p className="text-zinc-400 text-sm mt-1">
            {step === "phone" && "Telefon numaranızı girin"}
            {step === "otp" && "Doğrulama kodunu girin"}
            {step === "register" && "Bilgilerinizi tamamlayın"}
          </p>
        </div>

        {/* Form kartı */}
        <div className="bg-zinc-900 rounded-2xl shadow-sm border border-zinc-800 p-6">

          {/* ── A�?AMA 1: Telefon ── */}
          {step === "phone" && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1.5">
                  Telefon Numarası
                </label>
                <PhoneInput onChange={setPhone} disabled={isLoading} />
              </div>

              {/* Hata mesajı */}
              {error && (
                <p className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</p>
              )}

              <button
                onClick={handleSendOtp}
                disabled={isLoading || !phone}
                className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                {isLoading ? "Gönderiliyor..." : "Kod Gönder"}
              </button>
            </div>
          )}

          {/* ── A�?AMA 2: OTP ── */}
          {step === "otp" && (
            <div className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-3 text-center">
                  {phone} numarasına gönderilen kodu girin
                </label>
                <OTPInput onComplete={handleVerifyOtp} disabled={isLoading} />
              </div>

              {/* Hata mesajı */}
              {error && (
                <p className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2 text-center">{error}</p>
              )}

              {/* Yükleniyor göstergesi */}
              {isLoading && (
                <p className="text-center text-sm text-zinc-400">Doğrulanıyor...</p>
              )}

              {/* Tekrar gönder butonu — geri sayım bitince aktif */}
              <div className="text-center">
                {countdown > 0 ? (
                  <p className="text-sm text-zinc-400">
                    Tekrar gönder ({countdown}s)
                  </p>
                ) : (
                  <button
                    onClick={handleResendOtp}
                    disabled={isLoading}
                    className="text-sm text-zinc-200 font-medium underline underline-offset-2 disabled:opacity-50"
                  >
                    Kodu tekrar gönder
                  </button>
                )}
              </div>

              {/* Geri butonu */}
              <button
                onClick={() => { setStep("phone"); setError("") }}
                className="w-full text-sm text-zinc-400 hover:text-zinc-300"
              >
                ← Numarayı değiştir
              </button>
            </div>
          )}

          {/* ── A�?AMA 3: Kayıt (yeni kullanıcı) ── */}
          {step === "register" && (
            <div className="space-y-4">
              <p className="text-sm text-zinc-400 text-center">
                İlk girişiniz! Adınızı ve soyadınızı girin.
              </p>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1.5">Ad</label>
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  disabled={isLoading}
                  placeholder="Adınız"
                  className="w-full px-3 py-3 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent disabled:bg-zinc-950"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1.5">Soyad</label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  disabled={isLoading}
                  placeholder="Soyadınız"
                  className="w-full px-3 py-3 border border-zinc-700 rounded-lg text-base outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent disabled:bg-zinc-950"
                />
              </div>

              {/* Hata mesajı */}
              {error && (
                <p className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">{error}</p>
              )}

              <button
                onClick={handleRegister}
                disabled={isLoading || !firstName.trim() || !lastName.trim()}
                className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                {isLoading ? "Kaydediliyor..." : "Devam Et"}
              </button>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}


