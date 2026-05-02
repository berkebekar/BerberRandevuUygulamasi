"""
whatsapp/handlers.py — WhatsApp bot konuşma akışı.

Konuşma adımları (state machine):
  idle            → Ana menü gösterilir, buton beklenir
  date_select     → Müsait günler listesi, tarih seçimi beklenir
  time_select     → Seçilen günün saatleri, saat seçimi beklenir
  confirm         → Randevu özeti, onay/iptal beklenir
  otp_phone_collect → Web OTP için telefon numarası beklenir

Her step'te beklenmedik input gelirse, mevcut adım tekrar gösterilir.
"""

import logging
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.phone import normalize_tr_phone, phone_variants
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.auth import service as auth_service
from app.modules.booking import service as booking_service
from app.modules.schedule import service as schedule_service
from app.modules.schedule.schemas import SlotStatus
from app.modules.whatsapp import client as wa
from app.modules.whatsapp.state import (
    STEP_CONFIRM,
    STEP_DATE_SELECT,
    STEP_IDLE,
    STEP_OTP_PHONE,
    STEP_TIME_SELECT,
    ConversationState,
    clear_state,
    get_state,
    save_state,
)

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Europe/Istanbul")

_TR_DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
_TR_MONTHS = [
    "", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


# ─── Yardımcılar ─────────────────────────────────────────────────────────────

def _fmt_date(d: date) -> str:
    """Tarihi Türkçe'ye çevirir: 'Pazartesi 5 Mayıs'"""
    return f"{_TR_DAYS[d.weekday()]} {d.day} {_TR_MONTHS[d.month]}"


def _fmt_date_short(d: date) -> str:
    """Liste başlığı için kısa format: '05 May Pzt' (max 24 karakter)"""
    day_abbr = _TR_DAYS[d.weekday()][:3]
    month_abbr = _TR_MONTHS[d.month][:3]
    return f"{d.day:02d} {month_abbr} {day_abbr}"


def _phone_to_wa(normalized_phone: str) -> str:
    """'+905551234567' → '905551234567' (WA format, + olmadan)"""
    return normalized_phone.lstrip("+")


async def _get_tenant_by_phone_number_id(
    db: AsyncSession, phone_number_id: str
) -> Tenant | None:
    """Gelen webhook'un phone_number_id'sine göre tenant bulur."""
    result = await db.execute(
        select(Tenant).where(Tenant.whatsapp_phone_number_id == phone_number_id)
    )
    return result.scalar_one_or_none()


async def _get_or_create_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    wa_phone_raw: str,
    wa_name: str,
) -> User:
    """
    WA numarasıyla kullanıcı bulur; yoksa WhatsApp profil adıyla oluşturur.

    wa_phone_raw: "905551234567" (Meta'dan gelen, + olmadan)
    wa_name: WhatsApp profil adı ("Ahmet Yılmaz")
    """
    phone_with_plus = "+" + wa_phone_raw
    try:
        normalized = normalize_tr_phone(phone_with_plus)
    except Exception:
        normalized = phone_with_plus

    candidates = phone_variants(normalized)

    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.phone.in_(candidates),
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    parts = wa_name.strip().split(maxsplit=1)
    first_name = parts[0] if parts else "WA"
    last_name = parts[1] if len(parts) > 1 else "Kullanıcısı"

    user = User(
        tenant_id=tenant_id,
        phone=normalized,
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("WA'dan yeni kullanıcı oluşturuldu | tenant=%s phone=%s", tenant_id, normalized)
    return user


# ─── Mesaj Gönderme Yardımcıları ─────────────────────────────────────────────

async def _send_main_menu(
    phone_number_id: str,
    access_token: str,
    wa_phone: str,
    tenant_name: str,
) -> None:
    body = (
        f"Merhaba! *{tenant_name}* randevu sistemine hoş geldiniz.\n\n"
        "Aşağıdan yapmak istediğiniz işlemi seçin:"
    )
    await wa.send_buttons(
        phone_number_id,
        access_token,
        wa_phone,
        body,
        buttons=[
            wa.InteractiveButton(id="booking", title="Randevu Al"),
            wa.InteractiveButton(id="otp", title="Web Girisi OTP"),
        ],
        footer="Randevu almak icin 'Randevu Al'a basin.",
    )


async def _send_available_dates(
    phone_number_id: str,
    access_token: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """
    Sonraki 7 günün müsait tarihlerini liste olarak gönderir.
    Hiç müsait gün yoksa False döner.
    """
    today = datetime.now(TZ).date()
    start = today + timedelta(days=1)

    week_data = await schedule_service.get_slots_for_week(db, tenant_id, start)

    rows = []
    for day in week_data.week:
        if day.is_closed:
            continue
        avail = [s for s in day.slots if s.status == SlotStatus.available]
        if not avail:
            continue
        rows.append(
            wa.ListRow(
                id=f"date_{day.date.isoformat()}",
                title=_fmt_date_short(day.date),
                description=f"{len(avail)} musait saat",
            )
        )

    if not rows:
        return False

    sections = [wa.ListSection(title="Musait Gunler", rows=rows)]
    await wa.send_list(
        phone_number_id,
        access_token,
        wa_phone,
        body="Hangi gun randevu almak istiyorsunuz?",
        button_label="Gun Sec",
        sections=sections,
        footer="Iptal icin 'iptal' yazin.",
    )
    return True


async def _send_available_times(
    phone_number_id: str,
    access_token: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    selected_date: date,
    db: AsyncSession,
) -> bool:
    """
    Seçilen günün müsait saatlerini sabah/öğleden sonra bölümlerine ayırarak gönderir.
    Hiç müsait saat yoksa False döner.
    """
    day_slots = await schedule_service.get_slots_for_date(db, tenant_id, selected_date)

    if day_slots.is_closed:
        return False

    available = [s for s in day_slots.slots if s.status == SlotStatus.available]
    if not available:
        return False

    morning_rows = []
    afternoon_rows = []

    for slot in available:
        hour = int(slot.time.split(":")[0])
        end_time = slot.end_datetime.strftime("%H:%M")
        row = wa.ListRow(
            id=f"time_{slot.time}",
            title=f"{slot.time} - {end_time}",
        )
        if hour < 12:
            morning_rows.append(row)
        else:
            afternoon_rows.append(row)

    # WhatsApp API: toplam satır sayısı tüm section'larda 10'u geçemez
    morning_limited = morning_rows[:5]
    afternoon_limited = afternoon_rows[: 10 - len(morning_limited)]

    sections = []
    if morning_limited:
        sections.append(wa.ListSection(title="Sabah", rows=morning_limited))
    if afternoon_limited:
        sections.append(wa.ListSection(title="Ogleden Sonra", rows=afternoon_limited))

    date_label = _fmt_date(selected_date)
    await wa.send_list(
        phone_number_id,
        access_token,
        wa_phone,
        body=f"*{date_label}* icin saat secin:",
        button_label="Saat Sec",
        sections=sections,
        footer="Geri donmek icin 'geri' yazin.",
    )
    return True


async def _send_confirmation(
    phone_number_id: str,
    access_token: str,
    wa_phone: str,
    selected_date: date,
    selected_time: str,
    tenant_name: str,
) -> None:
    date_label = _fmt_date(selected_date)
    body = (
        f"*Randevu Ozeti*\n\n"
        f"Isletme: {tenant_name}\n"
        f"Gun:     {date_label}\n"
        f"Saat:    {selected_time}\n\n"
        "Onayliyor musunuz?"
    )
    await wa.send_buttons(
        phone_number_id,
        access_token,
        wa_phone,
        body,
        buttons=[
            wa.InteractiveButton(id="confirm_yes", title="Onayla"),
            wa.InteractiveButton(id="cancel_booking", title="Iptal Et"),
        ],
    )


# ─── Ana Dispatcher ───────────────────────────────────────────────────────────

async def handle_incoming(
    wa_phone: str,
    phone_number_id: str,
    wa_name: str,
    msg_type: str,
    content: str | None,
    db: AsyncSession,
) -> None:
    """
    Gelen WhatsApp mesajını işler.

    wa_phone      : gönderen numarası, "+" olmadan (örn: "905551234567")
    phone_number_id: hangi WA numarasına gönderildiği (Meta'dan)
    wa_name       : gönderenin WA profil adı
    msg_type      : "text" | "interactive"
    content       : text mesajı için metin, interactive için button/list id
    """
    # Tenant'ı bul
    tenant = await _get_tenant_by_phone_number_id(db, phone_number_id)
    if tenant is None:
        logger.warning("Bilinmeyen phone_number_id=%s — mesaj yoksayıldı", phone_number_id)
        return

    if not tenant.whatsapp_access_token:
        logger.error("Tenant %s için access_token eksik", tenant.id)
        return

    pid = phone_number_id
    tok = tenant.whatsapp_access_token
    tid = tenant.id

    # Mevcut state
    state = await get_state(pid, wa_phone)

    # "iptal" veya "geri" kelimeleri her adımda ana menüye döner
    if content and content.strip().lower() in ("iptal", "geri", "menu", "menü"):
        await clear_state(pid, wa_phone)
        await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── IDLE: Ana menü ────────────────────────────────────────────────────────
    if state.step == STEP_IDLE:
        if content == "booking":
            await _handle_booking_start(pid, tok, wa_phone, tid, state, db)
        elif content == "otp":
            await _handle_otp_start(pid, tok, wa_phone, tid, state)
        else:
            # İlk mesaj veya tanımlanamayan input → hoş geldin + menü
            state.tenant_id = str(tid)
            state.wa_name = wa_name
            await save_state(pid, wa_phone, state)
            await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── DATE_SELECT: Tarih seçimi ─────────────────────────────────────────────
    if state.step == STEP_DATE_SELECT:
        if content and content.startswith("date_"):
            selected_date_str = content[5:]  # "2026-05-10"
            try:
                selected_date = date.fromisoformat(selected_date_str)
            except ValueError:
                await _send_available_dates(pid, tok, wa_phone, tid, db)
                return
            await _handle_date_selected(pid, tok, wa_phone, tid, selected_date, state, db)
        else:
            # Beklenmedik input → tarihleri tekrar göster
            has_dates = await _send_available_dates(pid, tok, wa_phone, tid, db)
            if not has_dates:
                await wa.send_text(pid, tok, wa_phone, "Simdilik musait gun bulunmuyor. Daha sonra tekrar deneyin.")
                await clear_state(pid, wa_phone)
        return

    # ── TIME_SELECT: Saat seçimi ──────────────────────────────────────────────
    if state.step == STEP_TIME_SELECT:
        if content and content.startswith("time_"):
            selected_time = content[5:]  # "14:00"
            await _handle_time_selected(pid, tok, wa_phone, selected_time, state, tenant.name)
        else:
            if state.selected_date:
                selected_date = date.fromisoformat(state.selected_date)
                has_times = await _send_available_times(pid, tok, wa_phone, tid, selected_date, db)
                if not has_times:
                    await wa.send_text(pid, tok, wa_phone, "Bu gun icin musait saat kalmadi. Baska gun secin.")
                    state.step = STEP_DATE_SELECT
                    state.selected_date = None
                    await save_state(pid, wa_phone, state)
                    await _send_available_dates(pid, tok, wa_phone, tid, db)
            else:
                await clear_state(pid, wa_phone)
                await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── CONFIRM: Onay adımı ───────────────────────────────────────────────────
    if state.step == STEP_CONFIRM:
        if content == "confirm_yes":
            await _handle_booking_confirm(pid, tok, wa_phone, wa_name, state, tenant, db)
        elif content == "cancel_booking":
            await clear_state(pid, wa_phone)
            await wa.send_text(pid, tok, wa_phone, "Randevu iptal edildi. Baska bir islem icin mesaj gonderin.")
            # Kısa gecikme sonrası menüyü tekrar gönder
            await _send_main_menu(pid, tok, wa_phone, tenant.name)
        else:
            # Tekrar onayla mesajı göster
            if state.selected_date and state.selected_time:
                await _send_confirmation(
                    pid, tok, wa_phone,
                    date.fromisoformat(state.selected_date),
                    state.selected_time,
                    tenant.name,
                )
            else:
                await clear_state(pid, wa_phone)
                await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── OTP_PHONE: Web OTP için telefon ───────────────────────────────────────
    if state.step == STEP_OTP_PHONE:
        phone_input = (content or "").strip()
        if phone_input:
            await _handle_otp_phone_received(pid, tok, wa_phone, phone_input, state, tid, db)
        else:
            await wa.send_text(pid, tok, wa_phone, "Lutfen telefon numaranizi girin (ornek: 5551234567):")
        return

    # Bilinmeyen adım → sıfırla
    await clear_state(pid, wa_phone)
    await _send_main_menu(pid, tok, wa_phone, tenant.name)


# ─── Adım İşleyiciler ────────────────────────────────────────────────────────

async def _handle_booking_start(
    pid: str,
    tok: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    state: ConversationState,
    db: AsyncSession,
) -> None:
    """Randevu al butonuna basıldı → müsait günleri göster."""
    state.step = STEP_DATE_SELECT
    await save_state(pid, wa_phone, state)

    has_dates = await _send_available_dates(pid, tok, wa_phone, tenant_id, db)
    if not has_dates:
        await wa.send_text(
            pid, tok, wa_phone,
            "Simdilik onumuzdeki 7 gun icin musait randevu bulunmuyor.\n"
            "Lutfen daha sonra tekrar deneyin.",
        )
        await clear_state(pid, wa_phone)


async def _handle_otp_start(
    pid: str,
    tok: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    state: ConversationState,
) -> None:
    """Web OTP butonuna basıldı → telefon numarası iste."""
    state.step = STEP_OTP_PHONE
    state.tenant_id = str(tenant_id)
    await save_state(pid, wa_phone, state)
    await wa.send_text(
        pid, tok, wa_phone,
        "Web sitesine giris icin OTP kodu gonderelim.\n\n"
        "Telefon numaranizi girin (basindaki sifir olmadan):\n"
        "Ornek: *5551234567*",
    )


async def _handle_date_selected(
    pid: str,
    tok: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    selected_date: date,
    state: ConversationState,
    db: AsyncSession,
) -> None:
    """Tarih seçildi → o günün saatlerini göster."""
    state.step = STEP_TIME_SELECT
    state.selected_date = selected_date.isoformat()
    await save_state(pid, wa_phone, state)

    has_times = await _send_available_times(pid, tok, wa_phone, tenant_id, selected_date, db)
    if not has_times:
        await wa.send_text(
            pid, tok, wa_phone,
            f"{_fmt_date(selected_date)} icin musait saat kalmadi.\n"
            "Lutfen baska bir gun secin.",
        )
        state.step = STEP_DATE_SELECT
        state.selected_date = None
        await save_state(pid, wa_phone, state)
        await _send_available_dates(pid, tok, wa_phone, tenant_id, db)


async def _handle_time_selected(
    pid: str,
    tok: str,
    wa_phone: str,
    selected_time: str,
    state: ConversationState,
    tenant_name: str,
) -> None:
    """Saat seçildi → randevu özetini göster, onay iste."""
    state.step = STEP_CONFIRM
    state.selected_time = selected_time
    await save_state(pid, wa_phone, state)

    selected_date = date.fromisoformat(state.selected_date)  # type: ignore[arg-type]
    await _send_confirmation(pid, tok, wa_phone, selected_date, selected_time, tenant_name)


async def _handle_booking_confirm(
    pid: str,
    tok: str,
    wa_phone: str,
    wa_name: str,
    state: ConversationState,
    tenant: Tenant,
    db: AsyncSession,
) -> None:
    """Onay verildi → kullanıcı bul/oluştur → randevu oluştur."""
    if not state.selected_date or not state.selected_time:
        await clear_state(pid, wa_phone)
        await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    try:
        user = await _get_or_create_user(db, tenant.id, wa_phone, wa_name)
    except Exception as exc:
        logger.error("Kullanıcı oluşturma hatası | error=%s", exc)
        await wa.send_text(pid, tok, wa_phone, "Bir hata olustu. Lutfen tekrar deneyin.")
        await clear_state(pid, wa_phone)
        return

    selected_date = date.fromisoformat(state.selected_date)
    hour, minute = map(int, state.selected_time.split(":"))
    slot_dt = datetime.combine(selected_date, time(hour, minute), tzinfo=TZ)

    try:
        booking = await booking_service.create_booking(
            db,
            tenant.id,
            user.id,
            slot_dt,
            confirm_additional_same_day=True,
        )
    except Exception as exc:
        from fastapi import HTTPException
        if isinstance(exc, HTTPException):
            error_code = exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail)
            if error_code == "slot_taken":
                msg = "Uzgunum, bu saat az once baska biri tarafindan alindi.\nLutfen baska saat secin."
            elif error_code == "slot_blocked":
                msg = "Bu saat kapali.\nLutfen baska saat secin."
            elif error_code in ("slot_in_past", "invalid_slot"):
                msg = "Gecersiz randevu saati. Lutfen tekrar deneyin."
            else:
                msg = "Randevu olusturulamadi. Lutfen tekrar deneyin."
        else:
            msg = "Beklenmedik bir hata olustu. Lutfen tekrar deneyin."
            logger.error("Randevu oluşturma hatası | error=%s", exc)

        await wa.send_text(pid, tok, wa_phone, msg)
        # Saatleri tekrar göster
        state.step = STEP_TIME_SELECT
        state.selected_time = None
        await save_state(pid, wa_phone, state)
        await _send_available_times(pid, tok, wa_phone, tenant.id, selected_date, db)
        return

    # Başarılı
    await clear_state(pid, wa_phone)
    date_label = _fmt_date(selected_date)
    success_msg = (
        f"Randevunuz olusturuldu!\n\n"
        f"Isletme: {tenant.name}\n"
        f"Gun:     {date_label}\n"
        f"Saat:    {state.selected_time}\n\n"
        f"Randevu ID: {str(booking.id)[:8]}...\n\n"
        "Iptal icin web sitemizi ziyaret edebilirsiniz."
    )
    await wa.send_text(pid, tok, wa_phone, success_msg)
    logger.info("WA randevu oluşturuldu | booking_id=%s | user_id=%s", booking.id, user.id)


async def _handle_otp_phone_received(
    pid: str,
    tok: str,
    wa_phone: str,
    phone_input: str,
    state: ConversationState,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Kullanıcı telefon numarasını girdi → OTP üret ve WA mesajıyla gönder."""
    # "0" ile başlıyorsa kaldır, sonra normalize et
    cleaned = phone_input.strip().replace(" ", "").replace("-", "")
    if not cleaned.startswith("+"):
        cleaned = "+" + ("90" + cleaned.lstrip("0") if len(cleaned) <= 10 else cleaned)

    try:
        from app.core.phone import normalize_tr_phone
        normalized = normalize_tr_phone(cleaned)
    except Exception:
        await wa.send_text(
            pid, tok, wa_phone,
            "Gecersiz telefon numarasi. Lutfen tekrar deneyin.\n"
            "Ornek: *5551234567*",
        )
        return

    try:
        code = await auth_service.send_otp(db, tenant_id, normalized)
    except Exception as exc:
        from fastapi import HTTPException
        if isinstance(exc, HTTPException) and exc.status_code == 429:
            await wa.send_text(
                pid, tok, wa_phone,
                "Az once OTP gonderildi. 60 saniye bekleyip tekrar deneyin.",
            )
        else:
            logger.error("OTP gönderme hatası | error=%s", exc)
            await wa.send_text(pid, tok, wa_phone, "OTP gonderilemedi. Lutfen tekrar deneyin.")
        return

    await clear_state(pid, wa_phone)

    otp_msg = (
        f"Dogrulama kodunuz: *{code}*\n\n"
        "Bu kodu web sitesindeki giris sayfasina girin.\n"
        "Kod 5 dakika gecerlidir."
    )
    await wa.send_text(pid, tok, wa_phone, otp_msg)
    logger.info("WA OTP gonderildi | phone=%s", normalized)
