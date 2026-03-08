export const BOOKING_MAX_DAYS_AHEAD = 14

export type BookingDayItem = {
  date: string
  label: string
  shortDate: string
}

export function buildBookingDays(): BookingDayItem[] {
  const days: BookingDayItem[] = []
  const now = new Date()

  for (let i = 0; i < BOOKING_MAX_DAYS_AHEAD; i++) {
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
