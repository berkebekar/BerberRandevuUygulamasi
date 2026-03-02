/**
 * lib/api.ts - Backend API ile iletisim icin merkezi fetch wrapper.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ""

const STATUS_MESSAGES: Record<number, string> = {
  400: "Gecersiz istek. Lutfen bilgileri kontrol edin.",
  401: "Oturum suresi doldu. Lutfen tekrar giris yapin.",
  403: "Bu islem icin yetkiniz yok.",
  404: "Istenen kaynak bulunamadi.",
  409: "Bu islem mevcut verilerle cakisiyor.",
  422: "Gonderilen bilgiler eksik veya hatali.",
  429: "Cok fazla deneme. Lutfen 60 saniye bekleyin.",
  500: "Sunucu hatasi. Lutfen daha sonra tekrar deneyin.",
}

const ERROR_CODE_MESSAGES: Record<string, string> = {
  tenant_not_found: "Bu adreste aktif isletme bulunamadi.",
  tenant_inactive: "Bu isletme gecici olarak hizmet vermiyor.",
  tenant_required: "Isletme bilgisi eksik. Lutfen dogru adresten tekrar deneyin.",
  server_error: "Sunucuda beklenmeyen bir hata olustu. Lutfen tekrar deneyin.",
  not_authenticated: "Bu islem icin giris yapmaniz gerekiyor.",
  invalid_token: "Oturum gecersiz veya suresi dolmus. Lutfen tekrar giris yapin.",
  forbidden: "Bu islem icin yetkiniz bulunmuyor.",
  admin_not_found: "Yonetici hesabi bulunamadi.",
  user_not_found: "Kullanici hesabi bulunamadi.",
  slot_has_booking: "Bu saatte randevu var. Once randevuyu iptal edin.",
  slot_already_blocked: "Bu saat zaten kapali.",
  block_not_found: "Acilmak istenen blok kaydi bulunamadi.",
  missing_user_info: "Yeni musteri icin ad ve soyad bilgisi zorunludur.",
  user_creation_failed: "Musteri kaydi olusturulamadi. Lutfen tekrar deneyin.",
  slot_in_past: "Gecmis bir saat icin randevu olusturulamaz.",
  too_far_in_future: "En fazla 7 gun sonrasi icin randevu alabilirsiniz.",
  invalid_slot: "Secilen saat gecerli degil.",
  slot_taken: "Sectiginiz saat dolu.",
  slot_blocked: "Sectiginiz saat isletme tarafindan kapatildi.",
  already_booked_today: "Ayni gun icinde sadece bir randevu alabilirsiniz.",
  booking_not_found: "Randevu bulunamadi.",
  booking_cancellation_window_passed: "Randevu saatinden sonra iptal edilemez.",
  booking_not_started: "Bu islem sadece randevu saati geldikten sonra yapilabilir.",
  rate_limit_exceeded: "Cok sik deneme yaptiniz. Lutfen 60 saniye bekleyin.",
  otp_not_found: "Dogrulama kodu bulunamadi veya suresi doldu.",
  otp_invalid: "Dogrulama kodu hatali.",
  admin_already_exists: "Bu isletme icin yonetici hesabi zaten kayitli.",
  admin_not_registered: "Bu telefon numarasi ile kayitli yonetici bulunamadi.",
  invalid_credentials: "Email veya sifre hatali.",
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()

    if (typeof data?.error === "string") {
      return ERROR_CODE_MESSAGES[data.error] ?? STATUS_MESSAGES[res.status] ?? "Bir hata olustu."
    }

    if (typeof data?.detail === "string") {
      return data.detail
    }
  } catch {
    // no-op
  }

  return STATUS_MESSAGES[res.status] ?? "Islem tamamlanamadi. Lutfen tekrar deneyin."
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  })

  if (!res.ok) {
    const message = await parseError(res)
    if (
      res.status === 401 &&
      typeof window !== "undefined" &&
      !path.startsWith("/api/v1/auth/")
    ) {
      const currentPath = window.location.pathname
      const isAdminArea = currentPath.startsWith("/admin")
      const target = isAdminArea ? "/admin/login" : "/auth"
      if (currentPath !== target) {
        window.location.href = target
      }
    }
    const err = new Error(message) as Error & { status: number }
    err.status = res.status
    throw err
  }

  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

export async function apiPost<T = unknown>(
  path: string,
  body: unknown,
  init: RequestInit = {}
): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    ...init,
  })
}

export async function apiPut<T = unknown>(
  path: string,
  body: unknown
): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  })
}

export async function apiDelete<T = unknown>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" })
}
