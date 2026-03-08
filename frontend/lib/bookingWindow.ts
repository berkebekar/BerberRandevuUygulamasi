export const BOOKING_MAX_DAYS_AHEAD = 14

export type BookingDayItem = {
  date: string
  label: string
  shortDate: string
}

export function buildBookingDays(maxDaysAhead: number = BOOKING_MAX_DAYS_AHEAD): BookingDayItem[] {
  const days: BookingDayItem[] = []
  const now = new Date()
  const safeMaxDaysAhead = Number.isFinite(maxDaysAhead)
    ? Math.min(60, Math.max(1, Math.floor(maxDaysAhead)))
    : BOOKING_MAX_DAYS_AHEAD

  for (let i = 0; i <= safeMaxDaysAhead; i++) {
    const d = new Date(now)
    d.setDate(now.getDate() + i)

    const dateStr = d.toLocaleDateString("sv-SE", { timeZone: "Europe/Istanbul" })

    let label: string
    if (i === 0) label = "Bugun"
    else if (i === 1) label = "Yarin"
    else label = d.toLocaleDateString("tr-TR", { weekday: "short", timeZone: "Europe/Istanbul" })

    const shortDate = d.toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "short",
      timeZone: "Europe/Istanbul",
    })

    days.push({ date: dateStr, label, shortDate })
  }

  return days
}
