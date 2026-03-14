/**
 * app/admin/(protected)/page.tsx — Admin dashboard.
 *
 * Kurallar:
 * - Bugunun tarihi varsayilan
 * - Altinda randevu listesi + "Iptal Et" butonu
 * - Slot yonetimi: slota tikla -> Kapat / Ac
 * - Manuel randevu ekleme formu
 */

"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ActionConfirmSheet, AdminSlotGrid, PhoneInput } from "@/components"
import { apiDelete, apiPost } from "@/lib/api"
import { buildBookingDays } from "@/lib/bookingWindow"
import type {
  ConfirmAction,
} from "./types"
import {
  formatManualSlotTime,
  isSlotPastOrNow,
  mapAdminError,
  normalizeKey,
  TR_PHONE_REGEX,
} from "./utils"
import { useAdminOverview } from "./useAdminOverview"

export default function AdminDashboardPage() {
  const router = useRouter()
  const [maxBookingDaysAhead, setMaxBookingDaysAhead] = useState(14)
  const weekDays = useMemo(() => buildBookingDays(maxBookingDaysAhead), [maxBookingDaysAhead])

  // Secili tarih (varsayilan bugun)
  const [selectedDate, setSelectedDate] = useState(() => buildBookingDays(14)[0].date)

  // Global hata mesaji
  const [error, setError] = useState("")
  // Basarili islem sonrasi kisa bilgilendirme
  const [success, setSuccess] = useState("")
  // Kritik aksiyonlar once bu state'e yazilip sheet acilir
  const [pendingAction, setPendingAction] = useState<ConfirmAction | null>(null)
  // Sheet onaylandiktan sonra islem devam ederken loading
  const [confirmLoading, setConfirmLoading] = useState(false)

  // Manuel randevu formu
  const [showManual, setShowManual] = useState(false)
  const [manualPhone, setManualPhone] = useState("")
  const [manualFirstName, setManualFirstName] = useState("")
  const [manualLastName, setManualLastName] = useState("")
  const [manualSlot, setManualSlot] = useState("")
  const [manualLoading, setManualLoading] = useState(false)
  const successTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [slotMenuOpen, setSlotMenuOpen] = useState(false)
  const slotMenuRef = useRef<HTMLDivElement | null>(null)

  const {
    maxBookingDaysAhead: hookMaxDays,
    dashboard,
    dashboardLoading,
    slots,
    slotLoading,
    blockMap,
    fetchOverview,
  } = useAdminOverview(selectedDate, setError)
  const availableManualSlots = useMemo(
    () => slots.filter((slot) => slot.status === "available"),
    [slots]
  )

  /**
   * Tarih degistikce dashboard + slots + blocks cek.
   */
  useEffect(() => {
    if (weekDays.some((day) => day.date === selectedDate)) return
    if (weekDays[0]) {
      setSelectedDate(weekDays[0].date)
    }
  }, [weekDays, selectedDate])

  useEffect(() => {
    setMaxBookingDaysAhead(hookMaxDays)
  }, [hookMaxDays])

  useEffect(() => {
    if (!success) return
    if (successTimeout.current) {
      clearTimeout(successTimeout.current)
    }
    successTimeout.current = setTimeout(() => setSuccess(""), 4500)
    return () => {
      if (successTimeout.current) {
        clearTimeout(successTimeout.current)
        successTimeout.current = null
      }
    }
  }, [success])

  useEffect(() => {
    if (!slotMenuOpen) return
    const onClick = (event: MouseEvent) => {
      if (slotMenuRef.current && !slotMenuRef.current.contains(event.target as Node)) {
        setSlotMenuOpen(false)
      }
    }
    window.addEventListener("mousedown", onClick)
    return () => window.removeEventListener("mousedown", onClick)
  }, [slotMenuOpen])

  /**
   * Logout yap ve login'e yonlendir.
   */
  async function handleLogout() {
    try {
      await apiPost("/api/v1/auth/logout", {})
    } catch {
      // Logout hatasi olsa da yonlendir
    } finally {
      router.push("/auth")
    }
  }

  /**
   * Slot kapat.
   */
  async function handleBlock(slotDatetime: string) {
    // Direkt API cagirma yerine onay sheet'ini ac
    const timeText = new Date(slotDatetime).toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Europe/Istanbul",
    })
    setPendingAction({
      kind: "block_slot",
      title: "Slotu Kapat",
      description: `${selectedDate} ${timeText} slotu kapatilacak.`,
      payload: { slotDatetime },
    })
  }

  /**
   * Slot ac.
   */
  async function handleUnblock(blockId: string) {
    // Direkt API cagirma yerine onay sheet'ini ac
    setPendingAction({
      kind: "unblock_slot",
      title: "Slotu Ac",
      description: `${selectedDate} tarihindeki kapali slot tekrar acilacak.`,
      payload: { blockId },
    })
  }

  /**
   * Randevu iptal et.
   */
  async function handleCancelBooking(bookingId: string) {
    // Direkt API cagirma yerine onay sheet'ini ac
    const booking = (dashboard?.bookings ?? []).find((b) => b.id === bookingId)
    const timeText = booking
      ? new Date(booking.slot_time).toLocaleTimeString("tr-TR", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Europe/Istanbul",
        })
      : ""
    const person = booking ? `${booking.user_first_name} ${booking.user_last_name}` : "musteri"

    setPendingAction({
      kind: "cancel_booking",
      title: "Randevuyu Iptal Et",
      description: `${timeText} saatindeki ${person} randevusu iptal edilecek.`,
      payload: { bookingId },
    })
  }

  async function handleMarkNoShow(bookingId: string) {
    const booking = (dashboard?.bookings ?? []).find((b) => b.id === bookingId)
    const timeText = booking
      ? new Date(booking.slot_time).toLocaleTimeString("tr-TR", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Europe/Istanbul",
        })
      : ""
    const person = booking ? `${booking.user_first_name} ${booking.user_last_name}` : "musteri"

    setPendingAction({
      kind: "mark_no_show",
      title: "Gerceklesmedi Olarak Isaretle",
      description:
        `Bu randevuyu gerceklesmedi olarak isaretlemek ister misiniz? (${timeText} - ${person})`,
      payload: { bookingId },
    })
  }

  async function handleMarkConfirmed(bookingId: string) {
    const booking = (dashboard?.bookings ?? []).find((b) => b.id === bookingId)
    const timeText = booking
      ? new Date(booking.slot_time).toLocaleTimeString("tr-TR", {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: "Europe/Istanbul",
        })
      : ""
    const person = booking ? `${booking.user_first_name} ${booking.user_last_name}` : "musteri"

    setPendingAction({
      kind: "mark_confirmed",
      title: "Gerceklesti Olarak Isaretle",
      description:
        `Bu randevuyu gerceklesti olarak isaretlemek ister misiniz? (${timeText} - ${person})`,
      payload: { bookingId },
    })
  }

  /**
   * Manuel randevu olustur.
   */
  async function handleManualCreate() {
    // Saat secilmediyse isleme devam etme
    if (!manualSlot) {
      setError("Saat secimi zorunludur.")
      return
    }
    // Telefon opsiyonel; girilmisse format dogrulamasi yap.
    if (manualPhone && !TR_PHONE_REGEX.test(manualPhone)) {
      setError("Telefon girilecekse +90 ile 10 hane olacak sekilde girilmelidir.")
      return
    }

    setManualLoading(true)
    setError("")
    try {
      await apiPost("/api/v1/admin/bookings", {
        slot_time: manualSlot,
        phone: manualPhone || undefined,
        first_name: manualFirstName || undefined,
        last_name: manualLastName || undefined,
      })

      // Basarili: formu temizle ve verileri yenile
      setManualPhone("")
      setManualFirstName("")
      setManualLastName("")
      setManualSlot("")
      setShowManual(false)
      setSuccess("Islem basariyla tamamlandi.")
      await fetchOverview(selectedDate)
    } catch (err: unknown) {
      setError(mapAdminError(err))
    } finally {
      setManualLoading(false)
    }
  }

  /**
   * Slot listesine block_id entegre et.
   */
  const slotsWithBlocks = useMemo(() => {
    return slots.map((slot) => {
      const key = normalizeKey(slot.datetime)
      return {
        ...slot,
        block_id: blockMap[key],
      }
    })
  }, [slots, blockMap])

  /**
   * Onay sheet'inde secilen aksiyonu gercekten calistir.
   */
  async function handleConfirmAction() {
    if (!pendingAction) return

    setConfirmLoading(true)
    setError("")
    setSuccess("")

    try {
      // Hangi aksiyon secildiyse ona gore endpoint cagir
      if (pendingAction.kind === "block_slot") {
        await apiPost("/api/v1/admin/slots/block", {
          slot_datetime: pendingAction.payload.slotDatetime,
        })
        await fetchOverview(selectedDate)
      }

      if (pendingAction.kind === "unblock_slot") {
        await apiDelete(`/api/v1/admin/slots/block/${pendingAction.payload.blockId}`)
        await fetchOverview(selectedDate)
      }

      if (pendingAction.kind === "cancel_booking") {
        await apiDelete(`/api/v1/admin/bookings/${pendingAction.payload.bookingId}`)
        await fetchOverview(selectedDate)
      }

      if (pendingAction.kind === "mark_no_show") {
        await apiPost(`/api/v1/admin/bookings/${pendingAction.payload.bookingId}/mark-no-show`, {})
        await fetchOverview(selectedDate)
      }

      if (pendingAction.kind === "mark_confirmed") {
        await apiPost(`/api/v1/admin/bookings/${pendingAction.payload.bookingId}/mark-confirmed`, {})
        await fetchOverview(selectedDate)
      }

      setSuccess("Islem basariyla tamamlandi.")
      setPendingAction(null)
    } catch (err: unknown) {
      // Hata olursa sheet kapanir ve mesaj dashboard'da gorunur
      setPendingAction(null)
      setError(mapAdminError(err))
    } finally {
      setConfirmLoading(false)
    }
  }

  return (
    <>
      <div className="min-h-screen bg-zinc-950 pb-8">
      {/* Ust baslik */}
      <div className="bg-zinc-900 border-b border-zinc-800 px-4 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-100">Admin Paneli</h1>
            <p className="text-xs text-zinc-400">Gunluk ozet ve randevular</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/admin/statistics")}
              className="text-sm text-zinc-400 hover:text-zinc-300"
            >
              Istatistiklerim
            </button>
            <button
              onClick={() => router.push("/admin/settings")}
              className="text-sm text-zinc-400 hover:text-zinc-300"
            >
              Ayarlar
            </button>
            <button
              onClick={handleLogout}
              className="text-sm text-zinc-400 hover:text-zinc-300"
            >
              Cikis
            </button>
          </div>
        </div>
      </div>

      <div className="px-4 pt-4 space-y-6">
        {/* Tarih secici */}
        <div>
          <div className="mb-2">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-wide">
              TARİH SEÇİN
            </p>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 no-scrollbar">
            {weekDays.map((day) => {
              const isSelected = day.date === selectedDate
              return (
                <button
                  key={day.date}
                  onClick={() => setSelectedDate(day.date)}
                  className={`
                    flex-none flex flex-col items-center px-3 py-2.5 rounded-xl border transition-colors min-w-[60px]
                    ${isSelected
                      ? "bg-zinc-100 text-zinc-950 border-zinc-100"
                      : "bg-zinc-900 text-zinc-300 border-zinc-800 hover:border-zinc-300"
                    }
                  `}
                >
                  <span className="text-xs font-medium">{day.label}</span>
                  <span className={`text-xs mt-0.5 ${isSelected ? "text-zinc-700" : "text-zinc-500"}`}>
                    {day.shortDate}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Hata mesaji */}
        {/* Hata varsa gorester */}
        {error && (
          <div className="text-sm text-red-300 bg-red-500/10 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
        {/* Basari varsa kisa bilgi goster */}
        {success && (
          <div
            role="status"
            aria-live="polite"
            className="relative flex items-center justify-between gap-3 text-sm text-emerald-300 bg-emerald-500/10 rounded-lg px-3 py-2"
          >
            <span>{success}</span>
            <button
              type="button"
              aria-label="Mesajı kapat"
              className="text-emerald-100 hover:text-white"
              onClick={() => setSuccess("")}
            >
              ×
            </button>
          </div>
        )}

        {/* Randevu listesi */}
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-zinc-200">Bugünün Randevuları</h2>
            <span className="text-xs text-zinc-500">{selectedDate}</span>
          </div>

          {/* Dashboard yukleniyorsa loading yazisi */}
          {dashboardLoading && (
            <p className="text-sm text-zinc-400">Liste yukleniyor...</p>
          )}

          {/* Dashboard yuklendi ve liste bossa bilgi ver */}
          {!dashboardLoading && (dashboard?.bookings?.length ?? 0) === 0 && (
            <p className="text-sm text-zinc-400">Bu gun icin randevu yok.</p>
          )}

          {/* Dashboard yuklendi ve liste doluysa randevulari goster */}
          {!dashboardLoading && (dashboard?.bookings ?? []).length > 0 && (
            <div className="space-y-3">
              {(dashboard?.bookings ?? []).map((b) => {
                const isCancelled = b.status === "cancelled"
                const isNoShow = b.status === "no_show"
                const isPastBooking = isSlotPastOrNow(b.slot_time)
                const timeStr = new Date(b.slot_time).toLocaleTimeString("tr-TR", {
                  hour: "2-digit",
                  minute: "2-digit",
                  timeZone: "Europe/Istanbul",
                })
                const showPhone = TR_PHONE_REGEX.test(b.user_phone)
                const statusText = isCancelled
                  ? b.cancelled_by === "admin"
                    ? "Berber tarafindan iptal edildi"
                    : b.cancelled_by === "user"
                      ? "Musteri tarafindan iptal edildi"
                      : "Iptal edildi"
                  : isNoShow
                    ? "Randevu gerceklesmedi"
                    : isPastBooking
                      ? "Randevu Gerceklesti"
                      : ""

                return (
                  <div
                    key={b.id}
                    className={`flex items-center justify-between rounded-lg border px-3 py-2 ${
                      isCancelled ? "bg-zinc-950 border-zinc-800" : "bg-zinc-900 border-zinc-800"
                    }`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-zinc-100 break-words">
                        {timeStr} — {b.user_first_name} {b.user_last_name}
                      </p>
                      {showPhone && (
                        <p className="text-xs text-zinc-400 break-all">{b.user_phone}</p>
                      )}
                      {/* Randevu durum etiketi */}
                      {statusText && (
                        <p className="text-xs text-zinc-500 mt-0.5 break-words">{statusText}</p>
                      )}
                    </div>
                    {!isCancelled && !isNoShow && !isPastBooking && (
                      <button
                        onClick={() => handleCancelBooking(b.id)}
                        className="text-xs text-red-300 hover:text-red-200 shrink-0 ml-3"
                      >
                        Iptal Et
                      </button>
                    )}
                    {!isCancelled && isPastBooking && !isNoShow && (
                      <button
                        type="button"
                        aria-label="Gerceklesmedi olarak isaretle"
                        onClick={() => handleMarkNoShow(b.id)}
                        className="text-sm font-semibold text-emerald-300 hover:text-emerald-200 shrink-0 ml-3"
                      >
                        ✓
                      </button>
                    )}
                    {!isCancelled && isPastBooking && isNoShow && (
                      <button
                        type="button"
                        aria-label="Gerceklesti olarak isaretle"
                        onClick={() => handleMarkConfirmed(b.id)}
                        className="text-sm font-semibold text-red-300 hover:text-red-200 shrink-0 ml-3"
                      >
                        ✕
                      </button>
                    )}
                    {isCancelled && (
                      <button
                        disabled
                        className="text-xs text-zinc-600 shrink-0 ml-3"
                      >
                        Iptal Et
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Slot yonetimi */}
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-zinc-200">Randevu Yontemi</h2>
            <span className="text-xs text-zinc-500">{selectedDate}</span>
          </div>
          <p className="text-xs text-zinc-400 mb-3">
            Slotu kapatmak icin tiklayin. Kapali slotu tekrar acmak icin yeniden tiklayin.
          </p>
          <AdminSlotGrid
            slots={slotsWithBlocks}
            isLoading={slotLoading}
            onBlock={handleBlock}
            onUnblock={handleUnblock}
          />
        </div>

        {/* Manuel randevu ekleme */}
        <div className="bg-zinc-900 rounded-xl border border-zinc-800 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200">Manuel Randevu</h2>
            <button
              onClick={() => setShowManual((v) => !v)}
              className="text-sm text-zinc-200 underline underline-offset-2"
            >
              {showManual ? "Kapat" : "+ Randevu Ekle"}
            </button>
          </div>

          {/* Manuel randevu formu aciksa goster */}
          {showManual && (
            <div className="mt-4 space-y-3">
              {/* Secili tarih bilgisini goster */}
              <div className="text-xs text-zinc-400">
                Tarih: {selectedDate}
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Telefon (opsiyonel)
                </label>
                <PhoneInput onChange={setManualPhone} disabled={manualLoading} />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="min-w-0">
                  <label className="block text-xs font-medium text-zinc-400 mb-1">
                    Ad
                  </label>
                  <input
                    type="text"
                    value={manualFirstName}
                    onChange={(e) => setManualFirstName(e.target.value)}
                    placeholder="Ad"
                    className="w-full min-w-0 px-3 py-2.5 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
                  />
                </div>
                <div className="min-w-0">
                  <label className="block text-xs font-medium text-zinc-400 mb-1">
                    Soyad
                  </label>
                  <input
                    type="text"
                    value={manualLastName}
                    onChange={(e) => setManualLastName(e.target.value)}
                    placeholder="Soyad"
                    className="w-full min-w-0 px-3 py-2.5 border border-zinc-700 rounded-lg text-sm outline-none focus:ring-2 focus:ring-zinc-200 focus:border-transparent"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Saat Secimi
                </label>
                <div className="relative" ref={slotMenuRef}>
                  <button
                    type="button"
                    onClick={() => setSlotMenuOpen((prev) => !prev)}
                    className="w-full flex items-center justify-between px-3 py-2.5 border border-zinc-700 rounded-lg text-sm text-left bg-zinc-900 text-zinc-100"
                    aria-haspopup="listbox"
                    aria-expanded={slotMenuOpen}
                  >
                    <span>
                      {manualSlot ? formatManualSlotTime(manualSlot) : "Saat secin"}
                    </span>
                    <span className="text-xs text-zinc-400">{slotMenuOpen ? "▲" : "▼"}</span>
                  </button>
                  {slotMenuOpen && (
                    <div className="absolute bottom-full mb-2 w-full max-h-48 overflow-auto rounded-lg border border-zinc-700 bg-zinc-950 text-sm shadow-lg z-20 overscroll-contain">
                      {availableManualSlots.length === 0 ? (
                        <div className="px-3 py-2 text-zinc-400">Uygun saat yok</div>
                      ) : (
                        availableManualSlots.map((slot) => (
                          <button
                            key={slot.datetime}
                            type="button"
                            onClick={() => {
                              setManualSlot(slot.datetime)
                              setSlotMenuOpen(false)
                            }}
                            className="w-full text-left px-3 py-2 text-zinc-100 hover:bg-zinc-800 transition-colors"
                          >
                            {formatManualSlotTime(slot.datetime)}
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              <button
                onClick={handleManualCreate}
                disabled={manualLoading}
                className="w-full py-3 bg-zinc-100 text-zinc-950 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
              >
                {manualLoading ? "Kaydediliyor..." : "Randevu Olustur"}
              </button>
            </div>
          )}
        </div>
      </div>
      </div>
      {/* Kritik islemler icin alttan acilan onay sheet'i */}
      <ActionConfirmSheet
        open={Boolean(pendingAction)}
        title={pendingAction?.title ?? ""}
        description={pendingAction?.description ?? ""}
        confirmText="Onayla"
        cancelText="Vazgec"
        isLoading={confirmLoading}
        onCancel={() => setPendingAction(null)}
        onConfirm={handleConfirmAction}
      />
    </>
  )
}


