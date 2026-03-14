export const TR_PHONE_REGEX = /^\+90\d{10}$/

export function mapAdminError(err: unknown): string {
  if (!(err instanceof Error)) return "Beklenmeyen bir hata olustu."
  switch (err.message) {
    case "slot_has_booking":
      return "Bu slotta randevu var. Once randevuyu iptal edin."
    case "slot_already_blocked":
      return "Bu slot zaten kapali."
    case "block_not_found":
      return "Blok kaydi bulunamadi."
    case "missing_user_info":
      return "Bu telefon numarasi kayitli degil. Ad ve soyad gerekli."
    default:
      return err.message
  }
}

export function normalizeKey(datetime: string): string {
  return new Date(datetime).toISOString()
}

export function formatManualSlotTime(datetime: string) {
  return new Date(datetime).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  })
}

export function isSlotPastOrNow(slotTime: string): boolean {
  return new Date(slotTime).getTime() <= Date.now()
}
