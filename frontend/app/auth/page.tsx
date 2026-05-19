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

import { useCallback, useState, useEffect, useRef } from "react"
import type { ConfirmationResult } from "firebase/auth"
import { RecaptchaVerifier, signInWithPhoneNumber, signOut } from "firebase/auth"
import { PhoneInput, OTPInput, TenantUnavailable } from "@/components"
import { apiFetch, apiPost, isTenantAccessError } from "@/lib/api"
import { getFirebaseAuth } from "@/lib/firebase"

// Formun hangi aşamada olduğunu temsil eder
type Step = "phone" | "otp" | "register"
type OtpProvider = "whatsapp" | "firebase_sms" | "disabled"
type AuthNextStep = "admin" | "user" | "register" | "admin_otp"
const TR_PHONE_REGEX = /^\+90\d{10}$/

function getFirebaseOtpErrorMessage(err: unknown) {
  const code = err && typeof err === "object" && "code" in err ? String((err as { code?: unknown }).code) : ""
  const message = err instanceof Error ? err.message : ""

  if (code === "auth/invalid-app-credential" || code === "auth/captcha-check-failed") {
    return "SMS güvenlik doğrulaması başarısız oldu. Sayfayı yenileyip tekrar deneyin."
  }
  if (code === "auth/error-code:-39") {
    return "SMS şu anda gönderilemedi. Lütfen biraz sonra tekrar deneyin."
  }
  if (message.includes("reCAPTCHA has already been rendered")) {
    return "SMS güvenlik doğrulaması yenilenemedi. Lütfen tekrar deneyin."
  }
  if (code === "auth/missing-app-credential") {
    return "SMS güvenlik doğrulaması başlatılamadı. Sayfayı yenileyip tekrar deneyin."
  }
  if (code === "auth/too-many-requests") {
    return "Çok fazla SMS denemesi yapıldı. Lütfen biraz bekleyip tekrar deneyin."
  }
  if (code === "auth/quota-exceeded") {
    return "SMS gönderim limiti doldu. Lütfen daha sonra tekrar deneyin."
  }
  if (code === "auth/billing-not-enabled") {
    return "SMS gönderimi şu anda aktif değil. Lütfen işletme ile iletişime geçin."
  }
  if (code === "auth/invalid-phone-number") {
    return "Telefon numarası geçersiz. Lütfen numarayı kontrol edin."
  }
  if (code === "auth/network-request-failed") {
    return "Bağlantı sorunu nedeniyle SMS gönderilemedi. Lütfen tekrar deneyin."
  }
  if (code === "auth/code-expired") {
    return "Doğrulama kodunun süresi doldu. Lütfen yeni kod isteyin."
  }
  if (code === "auth/invalid-verification-code") {
    return "Doğrulama kodu hatalı. Lütfen tekrar kontrol edin."
  }
  if (code === "auth/session-expired") {
    return "Doğrulama oturumunun süresi doldu. Lütfen yeni kod isteyin."
  }
  return "SMS doğrulama tamamlanamadı. Lütfen tekrar deneyin."
}

export default function AuthPage() {
  // Hangi aşamadayız
  const [step, setStep] = useState<Step>("phone")

  // Form alanları
  const [phone, setPhone] = useState("")
  const [otp, setOtp] = useState("")
  const [firstName, setFirstName] = useState("")
  const [lastName, setLastName] = useState("")
  const [registrationToken, setRegistrationToken] = useState("")
  const [firebaseConfirmation, setFirebaseConfirmation] = useState<ConfirmationResult | null>(null)
  const recaptchaVerifierRef = useRef<RecaptchaVerifier | null>(null)
  const [recaptchaContainerKey, setRecaptchaContainerKey] = useState(0)

  // Yükleme ve hata durumları
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  // Tenant adı
  const [tenantName, setTenantName] = useState<string | null>(null)
  const [otpProvider, setOtpProvider] = useState<OtpProvider>("whatsapp")
  const [tenantError, setTenantError] = useState("")
  const [isTenantLoading, setIsTenantLoading] = useState(true)

  // OTP tekrar gönderme için geri sayım (saniye)
  const [countdown, setCountdown] = useState(0)

  const clearFirebaseState = useCallback(function clearFirebaseState() {
    recaptchaVerifierRef.current?.clear()
    recaptchaVerifierRef.current = null
    setFirebaseConfirmation(null)
    const container = document.getElementById("firebase-recaptcha-container")
    if (container) {
      container.innerHTML = ""
    }
  }, [])

  const resetFirebaseRecaptcha = useCallback(function resetFirebaseRecaptcha() {
    clearFirebaseState()
    setRecaptchaContainerKey((key) => key + 1)
  }, [clearFirebaseState])

  const refreshOtpProvider = useCallback(async function refreshOtpProvider() {
    const data = await apiFetch<{ name: string; otp_provider?: OtpProvider }>(
      "/api/v1/tenant/info",
      { cache: "no-store" }
    )
    const nextProvider = data.otp_provider ?? "whatsapp"
    setTenantName(data.name)
    setOtpProvider((currentProvider) => {
      if (currentProvider !== nextProvider) {
        clearFirebaseState()
        setOtp("")
        setCountdown(0)
      }
      return nextProvider
    })
    return nextProvider
  }, [clearFirebaseState])

  const sendFirebaseOtp = useCallback(async function sendFirebaseOtp() {
    const auth = getFirebaseAuth()
    resetFirebaseRecaptcha()
    const verifier = new RecaptchaVerifier(auth, "firebase-recaptcha-container", { size: "invisible" })
    recaptchaVerifierRef.current = verifier
    try {
      const confirmation = await signInWithPhoneNumber(auth, phone, verifier)
      setFirebaseConfirmation(confirmation)
    } catch (err) {
      resetFirebaseRecaptcha()
      throw new Error(getFirebaseOtpErrorMessage(err))
    }
  }, [phone, resetFirebaseRecaptcha])

  async function signOutFirebaseIfConfigured() {
    try {
      await signOut(getFirebaseAuth())
    } catch {
      // Firebase oturumu bizim backend oturumumuzdan ayrı; temizleme başarısızsa akışı bozma.
    }
  }

  useEffect(() => {
    async function loadTenantInfo() {
      try {
        await refreshOtpProvider()
      } catch (err: unknown) {
        if (isTenantAccessError(err)) {
          setTenantError(err.message)
        }
      } finally {
        setIsTenantLoading(false)
      }
    }
    loadTenantInfo()
  }, [refreshOtpProvider])

  useEffect(() => {
    return () => {
      clearFirebaseState()
    }
  }, [clearFirebaseState])

  useEffect(() => {
    clearFirebaseState()
    setOtp("")
    setCountdown(0)
  }, [clearFirebaseState, phone])

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
    if (tenantError) return

    if (!TR_PHONE_REGEX.test(phone)) {
      setError("Lütfen geçerli bir telefon numarası girin.")
      return
    }

    setError("")
    setIsLoading(true)
    try {
      const currentProvider = otpProvider
      if (currentProvider === "firebase_sms") {
        await sendFirebaseOtp()
      } else if (currentProvider === "disabled") {
        const res = await apiPost<{ next: AuthNextStep; registration_token?: string }>(
          "/api/v1/auth/otp-disabled-login",
          { phone }
        )
        if (res.next === "register") {
          setRegistrationToken(res.registration_token ?? "")
          setStep("register")
        } else if (res.next === "admin_otp") {
          setStep("otp")
          setCountdown(0)
        } else if (res.next === "admin") {
          window.location.assign("/admin")
        } else {
          window.location.assign("/")
        }
        return
      } else {
        await apiPost("/api/v1/auth/send-otp", { phone })
      }
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
      let res: { next: AuthNextStep; registration_token?: string }
      if (otpProvider === "firebase_sms") {
        if (!firebaseConfirmation) {
          throw new Error("Dogrulama oturumu bulunamadi. Kodu tekrar gonderin.")
        }
        let idToken: string | null = null
        try {
          const credential = await firebaseConfirmation.confirm(code)
          idToken = await credential.user.getIdToken()
          await signOutFirebaseIfConfigured()
        } catch {
          idToken = null
        }
        if (idToken) {
          res = await apiPost<{ next: AuthNextStep; registration_token?: string }>(
            "/api/v1/auth/firebase/verify-phone",
            { phone, id_token: idToken }
          )
        } else {
          res = await apiPost<{ next: AuthNextStep; registration_token?: string }>(
            "/api/v1/auth/firebase/verify-phone",
            { phone, code }
          )
        }
      } else if (otpProvider === "disabled") {
        res = await apiPost<{ next: AuthNextStep; registration_token?: string }>(
          "/api/v1/auth/otp-disabled/verify-admin",
          { phone, code }
        )
      } else {
        res = await apiPost<{ next: AuthNextStep; registration_token?: string }>(
          "/api/v1/auth/verify-otp",
          { phone, code }
        )
      }

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
    if (tenantError) return

    if (countdown > 0) return
    if (!TR_PHONE_REGEX.test(phone)) {
      setStep("phone")
      setError("Lütfen geçerli bir telefon numarası girin.")
      return
    }
    setError("")
    setIsLoading(true)
    try {
      const currentProvider = await refreshOtpProvider()
      if (currentProvider === "firebase_sms") {
        await sendFirebaseOtp()
      } else if (currentProvider === "disabled") {
        return
      } else {
        await apiPost("/api/v1/auth/send-otp", { phone })
      }
      setCountdown(60)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Kod gönderilemedi.")
    } finally {
      setIsLoading(false)
    }
  }

  if (isTenantLoading) {
    return (
      <div className="min-h-[100dvh] bg-zinc-950 px-4 py-6 flex items-center justify-center">
        <p className="text-sm text-zinc-500">Yukleniyor...</p>
      </div>
    )
  }

  if (tenantError) {
    return <TenantUnavailable message={tenantError} />
  }

  return (
    // Mobile-first: icerigi ortala; dar ekranlarda taskinligi scroll ile yonet.
    <div className="min-h-[100dvh] bg-zinc-950 px-4 py-6 sm:py-10 flex items-center justify-center overflow-y-auto">
      <div className="w-full max-w-sm mx-auto">

        {/* Logo / Başlık */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">✂️</div>
          <h1 className="text-2xl font-bold text-zinc-100">
            {tenantName ? `${tenantName} Randevu Paneli` : "Randevu Paneli"}
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            {step === "phone" && "Telefon numaranızı başında 0 olmadan girin"}
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
                  {otpProvider === "disabled"
                    ? `${phone} numarasi icin gecis kodunu girin`
                    : otpProvider === "firebase_sms"
                    ? `${phone} numarasina SMS ile gonderilen kodu girin`
                    : `${phone} numarasına WhatsApp'tan gönderilen kodu girin`}
                </label>
                {otpProvider === "firebase_sms" && (
                  <p className="mb-3 text-center text-xs text-zinc-400">
                    SMS spam kutunuza düşmüş olabilir, spam kutunuzu kontrol edin.
                  </p>
                )}
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

              {otpProvider !== "disabled" && (
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
              )}

              {/* Geri butonu */}
              <button
                onClick={() => { clearFirebaseState(); setOtp(""); setStep("phone"); setError("") }}
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
        <div key={recaptchaContainerKey} id="firebase-recaptcha-container" />
        <div className="mt-5 text-center text-xs">
          <a
            href="https://bbsoft.com.tr"
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-zinc-300 underline underline-offset-4 hover:text-white"
          >
            Bu ürün için bize ulaşın
          </a>
        </div>
      </div>
    </div>
  )
}


