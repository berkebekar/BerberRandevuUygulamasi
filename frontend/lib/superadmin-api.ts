/**
 * lib/superadmin-api.ts - Super admin endpoint'leri icin merkezi fetch wrapper.
 */

const SUPERADMIN_STATUS_MESSAGES: Record<number, string> = {
  400: "Gecersiz istek. Lutfen bilgileri kontrol edin.",
  401: "Super admin oturumu gecersiz veya suresi dolmus.",
  403: "Bu super admin islemi icin yetkiniz yok.",
  404: "Istenen kaynak bulunamadi.",
  409: "Bu islem mevcut verilerle cakisiyor.",
  422: "Gonderilen bilgiler eksik veya hatali.",
  429: "Cok fazla deneme. Lutfen biraz bekleyin.",
  500: "Sunucu hatasi. Lutfen daha sonra tekrar deneyin.",
}

const SUPERADMIN_ERROR_MESSAGES: Record<string, string> = {
  not_authenticated: "Super admin girisi gerekli.",
  invalid_token: "Super admin oturumu gecersiz veya suresi dolmus.",
  forbidden: "Bu super admin islemi icin yetkiniz yok.",
  super_admin_not_found: "Super admin hesabi bulunamadi.",
  super_admin_inactive: "Super admin hesabi pasif durumda.",
  session_revoked: "Bu oturum sonlandirildi. Lutfen tekrar giris yapin.",
  invalid_credentials: "Kullanici adi veya sifre hatali.",
  tenant_not_found: "Tenant bulunamadi.",
  tenant_deleted: "Tenant silinmis durumda.",
  admin_not_found: "Tenant yoneticisi bulunamadi.",
  user_not_found: "Kullanici bulunamadi.",
  user_deleted: "Kullanici silinmis durumda.",
  error_log_not_found: "Hata log kaydi bulunamadi.",
}

export type SuperAdminApiErrorPayload = Record<string, unknown>

type ParsedSuperAdminApiError = {
  message: string
  errorCode?: string
  payload?: SuperAdminApiErrorPayload
}

export class SuperAdminApiError extends Error {
  status: number
  errorCode?: string
  payload?: SuperAdminApiErrorPayload

  constructor(params: { message: string; status: number; errorCode?: string; payload?: SuperAdminApiErrorPayload }) {
    super(params.message)
    this.name = "SuperAdminApiError"
    this.status = params.status
    this.errorCode = params.errorCode
    this.payload = params.payload
  }
}

async function parseSuperAdminError(res: Response): Promise<ParsedSuperAdminApiError> {
  try {
    const data = (await res.json()) as SuperAdminApiErrorPayload
    const rawError = data?.error

    if (typeof rawError === "string") {
      if (rawError === "too_many_attempts" && typeof data.retry_after === "number") {
        const minutes = Math.ceil((data.retry_after as number) / 60)
        return {
          message: `Cok fazla basarisiz deneme. ${minutes} dakika sonra tekrar deneyin.`,
          errorCode: rawError,
          payload: data,
        }
      }
      return {
        message: SUPERADMIN_ERROR_MESSAGES[rawError] ?? SUPERADMIN_STATUS_MESSAGES[res.status] ?? "Islem tamamlanamadi.",
        errorCode: rawError,
        payload: data,
      }
    }

    if (typeof data?.detail === "string") {
      return { message: data.detail, payload: data }
    }
  } catch {
    // no-op
  }

  return { message: SUPERADMIN_STATUS_MESSAGES[res.status] ?? "Islem tamamlanamadi." }
}

export async function superAdminFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  if (!path.startsWith("/api/v1/superadmin/")) {
    throw new Error("superAdminFetch sadece /api/v1/superadmin/* path'leri ile kullanilabilir.")
  }

  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  })

  if (!response.ok) {
    const parsed = await parseSuperAdminError(response)
    throw new SuperAdminApiError({
      message: parsed.message,
      status: response.status,
      errorCode: parsed.errorCode,
      payload: parsed.payload,
    })
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export async function superAdminPost<T = unknown>(path: string, body: unknown, init: RequestInit = {}): Promise<T> {
  return superAdminFetch<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    ...init,
  })
}

export async function superAdminGet<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  return superAdminFetch<T>(path, {
    method: "GET",
    ...init,
  })
}

export async function superAdminPut<T = unknown>(path: string, body: unknown, init: RequestInit = {}): Promise<T> {
  return superAdminFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
    ...init,
  })
}

export async function superAdminDelete<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  return superAdminFetch<T>(path, {
    method: "DELETE",
    ...init,
  })
}

/**
 * Protected layout'da server tarafinda cookie + backend dogrulamasi icin kullanilir.
 */
export async function validateSuperAdminSession(cookieHeader: string): Promise<boolean> {
  const backendBaseUrl = process.env.BACKEND_URL ?? "http://localhost:8000"
  const response = await fetch(`${backendBaseUrl}/api/v1/superadmin/stats/overview`, {
    method: "GET",
    headers: {
      Cookie: cookieHeader,
    },
    cache: "no-store",
  })
  return response.ok
}
