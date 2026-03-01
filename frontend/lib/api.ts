/**
 * lib/api.ts — Backend API ile iletişim için merkezi fetch wrapper.
 *
 * Neden bu dosya var?
 * - Her yerde tekrar tekrar aynı fetch ayarlarını yazmamak için
 * - Cookie'leri (credentials: 'include') otomatik eklemek için
 * - API hata mesajlarını tek noktada yakalamak için
 * - Türkçe hata mesajlarını buradan yönetmek için
 */

// Backend URL — geliştirmede Docker proxy üzerinden, üretimde Railway URL'i
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ""

/**
 * HTTP durum kodlarını Türkçe kullanıcı mesajlarına çevirir.
 * Böylece "Something went wrong" gibi anlamsız mesajlar gösterilmez.
 */
const STATUS_MESSAGES: Record<number, string> = {
  400: "Geçersiz istek. Lütfen bilgileri kontrol edin.",
  401: "Oturum süresi doldu. Lütfen tekrar giriş yapın.",
  403: "Bu işlem için yetkiniz yok.",
  404: "İstenen kaynak bulunamadı.",
  409: "Bu bilgi zaten kullanımda veya çakışma var.",
  429: "Çok fazla deneme. Lütfen 60 saniye bekleyin.",
  500: "Sunucu hatası. Lütfen daha sonra tekrar deneyin.",
}

/**
 * API'den dönen hata yanıtını Türkçe mesaja dönüştürür.
 * Önce backend'in döndürdüğü 'error' alanına bakar,
 * bulamazsa HTTP durum koduna göre genel mesaj döner.
 */
async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    // Backend her hata için {"error": "..."} formatı döndürür
    if (data.error) return data.error
  } catch {
    // JSON parse edilemezse durum koduna göre devam et
  }
  return STATUS_MESSAGES[res.status] ?? `Hata kodu: ${res.status}`
}

/**
 * Merkezi fetch fonksiyonu.
 * path: "/api/v1/slots?date=2026-02-25" gibi tam yol
 * init: fetch seçenekleri (method, body, headers vb.)
 * Hata durumunda Error fırlatır, başarıda JSON döner.
 */
export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    // credentials: 'include' — tarayıcı HTTP-only cookie'leri otomatik gönderir
    // Bu olmadan oturum cookie'si istekle birlikte gitmez
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  })

  // 2xx dışındaki tüm durum kodları hata sayılır
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

  // 204 No Content gibi gövdesiz yanıtlarda JSON parse etme
  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

/**
 * JSON body'si olan POST/PUT istekleri için kısayol.
 */
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

/**
 * JSON body'si olan PUT istekleri için kısayol.
 */
export async function apiPut<T = unknown>(
  path: string,
  body: unknown
): Promise<T> {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  })
}

/**
 * DELETE isteği için kısayol.
 */
export async function apiDelete<T = unknown>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: "DELETE" })
}
