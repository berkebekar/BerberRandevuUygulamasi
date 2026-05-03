"""
whatsapp/handlers.py — WhatsApp bot konuşma akışı.

Konuşma adımları (state machine):
  idle         → Ana menü gösterilir, buton beklenir
  name_collect → Yeni kullanıcı: isim ve soyisim beklenir
  date_select  → Müsait günler listesi, tarih seçimi beklenir
  time_select  → Seçilen günün saatleri, saat seçimi beklenir
  confirm      → Randevu özeti, onay/iptal beklenir

Her step'te beklenmedik input gelirse, mevcut adım tekrar gösterilir.
"""

import logging
import re
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.phone import normalize_tr_phone, phone_variants
from app.models.barber_profile import BarberProfile
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.modules.booking import service as booking_service
from app.modules.schedule import service as schedule_service
from app.modules.schedule.schemas import SlotStatus
from app.modules.whatsapp import client as wa
from app.modules.whatsapp.state import (
    STEP_CONFIRM,
    STEP_DATE_SELECT,
    STEP_IDLE,
    STEP_NAME_COLLECT,
    STEP_TIME_SELECT,
    ConversationState,
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
    """Tarihi Türkçe'ye çevirir: '09 Mayıs Cumartesi'"""
    return f"{d.day:02d} {_TR_MONTHS[d.month]} {_TR_DAYS[d.weekday()]}"


def _fmt_date_short(d: date) -> str:
    return f"{d.day:02d} {_TR_MONTHS[d.month]} {_TR_DAYS[d.weekday()]}"


async def _get_tenant_by_subdomain(db: AsyncSession, subdomain: str) -> Tenant | None:
    result = await db.execute(
        select(Tenant).where(Tenant.subdomain == subdomain, Tenant.is_active.is_(True))
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


async def _find_user_tenants(db: AsyncSession, wa_phone: str) -> list[Tenant]:
    """Bu WA numarasının DB'de kayıtlı olduğu aktif tenant'ları döner."""
    phone_with_plus = "+" + wa_phone
    try:
        normalized = normalize_tr_phone(phone_with_plus)
    except Exception:
        normalized = phone_with_plus
    candidates = phone_variants(normalized)
    result = await db.execute(
        select(Tenant)
        .join(User, User.tenant_id == Tenant.id)
        .where(User.phone.in_(candidates), Tenant.is_active.is_(True))
        .order_by(Tenant.name)
    )
    return list(result.scalars().all())


# ─── Mesaj Gönderme Yardımcıları ─────────────────────────────────────────────

async def _reset_to_idle(
    pid: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    wa_name: str | None = None,
) -> None:
    """Booking alanlarını sıfırlar ama tenant_id ve wa_name'i korur."""
    fresh = ConversationState(
        step=STEP_IDLE,
        tenant_id=str(tenant_id),
        wa_name=wa_name,
    )
    await save_state(pid, wa_phone, fresh)


async def _send_tenant_list(
    pid: str,
    tok: str,
    wa_phone: str,
    db: AsyncSession,
    tenants: list[Tenant] | None = None,
    body: str = "Hangi isletmeyle gorusmek istiyorsunuz?",
    section_title: str = "Isletmeler",
) -> None:
    """Tenant listesini WA list mesajı olarak gönderir.

    tenants: verilirse bu liste kullanılır, yoksa tüm aktif tenantlar sorgulanır.
    """
    if tenants is None:
        result = await db.execute(
            select(Tenant).where(Tenant.is_active.is_(True)).order_by(Tenant.name)
        )
        tenants = list(result.scalars().all())

    if not tenants:
        await wa.send_text(pid, tok, wa_phone, "Simdilik kayitli isletme bulunmuyor.")
        return

    show = tenants[:9]
    rows = [
        wa.ListRow(id=f"select_tenant_{t.subdomain}", title=t.name)
        for t in show
    ]
    if len(tenants) > 9:
        rows.append(wa.ListRow(id="tenant_more", title="Diger isletmeler..."))

    sections = [wa.ListSection(title=section_title, rows=rows)]
    await wa.send_list(
        pid, tok, wa_phone,
        body=body,
        button_label="Isletme Sec",
        sections=sections,
        footer="Isletmenin size verdigi linki kullanabilirsiniz.",
    )


async def _handle_tenant_selection(
    pid: str,
    tok: str,
    wa_phone: str,
    wa_name: str,
    content: str | None,
    state: "ConversationState",
    db: AsyncSession,
    known_tenants: list[Tenant] | None = None,
) -> None:
    """
    Henüz tenant seçilmemiş kullanıcı için routing.

    Öncelik sırası:
    1. content bir subdomain keyword veya listeden seçim ise → o tenant'a bağla
    2. content keyword değilse → known_tenants'a göre:
       - 1 tenant → otomatik bağla (kullanıcı zaten o berbere kayıtlı)
       - Birden fazla → o kullanıcının berberlerini listele
       - Hiç yok → tüm aktif tenant listesini göster
    """
    if content:
        slug = content.strip().lower()

        if slug == "tenant_more":
            await wa.send_text(
                pid, tok, wa_phone,
                "Diger isletmeler icin lutfen isletmenin size verdigi linki kullanin.",
            )
            return

        if slug.startswith("select_tenant_"):
            slug = slug[14:]

        tenant = await _get_tenant_by_subdomain(db, slug)
        if tenant:
            state.tenant_id = str(tenant.id)
            state.wa_name = wa_name
            await save_state(pid, wa_phone, state)
            await _send_main_menu(pid, tok, wa_phone, tenant.name)
            return

    # Content subdomain eşleşmedi — DB bilgisine göre davran
    if known_tenants is not None:
        if len(known_tenants) == 1:
            # Daha önce bu berbere kayıtlı → otomatik bağla
            tenant = known_tenants[0]
            state.tenant_id = str(tenant.id)
            state.wa_name = wa_name
            await save_state(pid, wa_phone, state)
            await _send_main_menu(pid, tok, wa_phone, tenant.name)
            return
        if len(known_tenants) > 1:
            # Birden fazla berbere kayıtlı → sadece onları listele
            await _send_tenant_list(
                pid, tok, wa_phone, db,
                tenants=known_tenants,
                body="Hangi isletmeyle gorusmek istiyorsunuz?",
                section_title="Randevu Aldiginiz Isletmeler",
            )
            return

    # Hiç kayıt yok (yeni kullanıcı) → tüm liste
    await _send_tenant_list(pid, tok, wa_phone, db)


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
            wa.InteractiveButton(id="my_bookings", title="Mevcut Randevularım"),
        ],
        footer="Yapmak istediginiz islemi secin.",
    )


async def _send_available_dates(
    phone_number_id: str,
    access_token: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """
    Berberin ileri tarih limitine kadar müsait günleri liste olarak gönderir.
    WhatsApp max 10 row: 9 gün gösterilir, fazlası varsa 10. satır web linki olur.
    Hiç müsait gün yoksa False döner.
    """
    today = datetime.now(TZ).date()

    profile_result = await db.execute(
        select(BarberProfile).where(BarberProfile.tenant_id == tenant_id)
    )
    profile = profile_result.scalar_one_or_none()
    max_days = profile.max_booking_days_ahead if profile else 14

    week_data = await schedule_service.get_slots_for_week(db, tenant_id, today, days=max_days)

    available_days = []
    for day in week_data.week:
        if day.is_closed:
            continue
        avail = [s for s in day.slots if s.status == SlotStatus.available]
        if avail:
            available_days.append((day, len(avail)))

    if not available_days:
        return False

    add_more = len(available_days) > 9
    show_days = available_days[:9] if add_more else available_days

    rows = [
        wa.ListRow(
            id=f"date_{day.date.isoformat()}",
            title=_fmt_date_short(day.date),
        )
        for day, count in show_days
    ]

    if add_more:
        rows.append(
            wa.ListRow(
                id="date_more",
                title="Daha Ileri Bir Tarih Sec",
            )
        )

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


_SLOT_PAGE_SIZE = 8


async def _send_available_times(
    phone_number_id: str,
    access_token: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    selected_date: date,
    db: AsyncSession,
    offset: int = 0,
) -> bool:
    """
    Seçilen günün müsait saatlerini sayfalı liste olarak gönderir.
    Hiç müsait saat yoksa False döner.

    offset: gösterilecek ilk slot'un indeksi (_SLOT_PAGE_SIZE adımlarıyla artar)
    """
    day_slots = await schedule_service.get_slots_for_date(db, tenant_id, selected_date)

    if day_slots.is_closed:
        return False

    available = [s for s in day_slots.slots if s.status == SlotStatus.available]
    if not available:
        return False

    total = len(available)
    page = available[offset: offset + _SLOT_PAGE_SIZE]

    rows: list[wa.ListRow] = []

    if offset > 0:
        rows.append(wa.ListRow(id="slot_prev", title="<- Onceki saatler"))

    for slot in page:
        rows.append(wa.ListRow(id=f"time_{slot.time}", title=slot.time))

    if offset + _SLOT_PAGE_SIZE < total:
        rows.append(wa.ListRow(id="slot_next", title="-> Sonraki saatler"))

    sections = [wa.ListSection(title="Uygun Saatler", rows=rows)]
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
    phone_number_id: webhook'tan gelen Meta phone number ID (state anahtarı için)
    wa_name       : gönderenin WA profil adı
    msg_type      : "text" | "interactive"
    content       : text mesajı için metin, interactive için button/list id
    """
    settings = get_settings()
    tok = settings.wa_access_token
    pid = phone_number_id

    if not tok:
        logger.error("WA_ACCESS_TOKEN ayarlanmamis — mesaj yoksayildi")
        return

    # Mevcut state
    state = await get_state(pid, wa_phone)

    # Tenant'ı state'den çöz; yoksa subdomain keyword ile bul
    tenant: Tenant | None = None
    if state.tenant_id:
        try:
            t_res = await db.execute(
                select(Tenant).where(
                    Tenant.id == uuid.UUID(state.tenant_id),
                    Tenant.is_active.is_(True),
                )
            )
            tenant = t_res.scalar_one_or_none()
        except Exception:
            pass

    if tenant is None:
        known_tenants = await _find_user_tenants(db, wa_phone)
        await _handle_tenant_selection(pid, tok, wa_phone, wa_name, content, state, db, known_tenants=known_tenants)
        return

    tid = tenant.id

    # "iptal" veya "geri" kelimeleri her adımda ana menüye döner
    if content and content.strip().lower() in ("iptal", "geri", "menu", "menü"):
        await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
        await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── IDLE: Ana menü ────────────────────────────────────────────────────────
    if state.step == STEP_IDLE:
        if content == "booking":
            await _handle_booking_start(pid, tok, wa_phone, tid, state, db)
        elif content == "my_bookings":
            await _handle_my_bookings(pid, tok, wa_phone, tid, tenant, db)
        else:
            # İlk mesaj veya tanımlanamayan input → hoş geldin + menü
            state.tenant_id = str(tid)
            state.wa_name = wa_name
            await save_state(pid, wa_phone, state)
            await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── NAME_COLLECT: Yeni kullanıcı isim/soyisim toplama ────────────────────
    if state.step == STEP_NAME_COLLECT:
        if content:
            await _handle_name_received(pid, tok, wa_phone, content, state, tenant, db)
        else:
            await wa.send_text(
                pid, tok, wa_phone,
                "Lutfen adinizi ve soyadinizi yazin:\n(Ornek: Ahmet Yilmaz)",
            )
        return

    # ── DATE_SELECT: Tarih seçimi ─────────────────────────────────────────────
    if state.step == STEP_DATE_SELECT:
        if content == "date_more":
            site_url = f"https://{tenant.subdomain}.bbsoft.com.tr"
            await wa.send_text(
                pid, tok, wa_phone,
                f"Daha ileri bir tarihe randevu almak icin web sitemizi ziyaret edebilirsiniz:\n\n{site_url}",
            )
            await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
            return
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
                await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
        return

    # ── TIME_SELECT: Saat seçimi ──────────────────────────────────────────────
    if state.step == STEP_TIME_SELECT:
        if content == "slot_next":
            state.slot_offset += _SLOT_PAGE_SIZE
            await save_state(pid, wa_phone, state)
            if state.selected_date:
                await _send_available_times(
                    pid, tok, wa_phone, tid,
                    date.fromisoformat(state.selected_date), db,
                    offset=state.slot_offset,
                )
            return
        if content == "slot_prev":
            state.slot_offset = max(0, state.slot_offset - _SLOT_PAGE_SIZE)
            await save_state(pid, wa_phone, state)
            if state.selected_date:
                await _send_available_times(
                    pid, tok, wa_phone, tid,
                    date.fromisoformat(state.selected_date), db,
                    offset=state.slot_offset,
                )
            return
        if content and content.startswith("time_"):
            selected_time = content[5:]  # "14:00"
            await _handle_time_selected(pid, tok, wa_phone, selected_time, state, tenant.name)
        else:
            if state.selected_date:
                selected_date = date.fromisoformat(state.selected_date)
                has_times = await _send_available_times(
                    pid, tok, wa_phone, tid, selected_date, db,
                    offset=state.slot_offset,
                )
                if not has_times:
                    await wa.send_text(pid, tok, wa_phone, "Bu gun icin musait saat kalmadi. Baska gun secin.")
                    state.step = STEP_DATE_SELECT
                    state.selected_date = None
                    state.slot_offset = 0
                    await save_state(pid, wa_phone, state)
                    await _send_available_dates(pid, tok, wa_phone, tid, db)
            else:
                await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
                await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # ── CONFIRM: Onay adımı ───────────────────────────────────────────────────
    if state.step == STEP_CONFIRM:
        if content == "confirm_yes":
            await _handle_booking_confirm(pid, tok, wa_phone, wa_name, state, tenant, db)
        elif content == "cancel_booking":
            await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
            await wa.send_text(pid, tok, wa_phone, "Randevu iptal edildi. Baska bir islem icin mesaj gonderin.")
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
                await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
                await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    # Bilinmeyen adım → sıfırla
    await _reset_to_idle(pid, wa_phone, tid, state.wa_name)
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
    """Randevu al butonuna basıldı → kullanıcı kayıtlıysa tarihleri göster, değilse isim sor."""
    phone_with_plus = "+" + wa_phone
    try:
        normalized = normalize_tr_phone(phone_with_plus)
    except Exception:
        normalized = phone_with_plus

    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.phone.in_(phone_variants(normalized)),
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user is None:
        state.step = STEP_NAME_COLLECT
        await save_state(pid, wa_phone, state)
        await wa.send_text(
            pid, tok, wa_phone,
            "Sistemde kaydiniz bulunmuyor.\n\n"
            "Randevu almak icin lutfen *adinizi ve soyadinizi* yazin:\n"
            "(Ornek: Ahmet Yilmaz)",
        )
        return

    state.step = STEP_DATE_SELECT
    state.user_id = str(existing_user.id)
    await save_state(pid, wa_phone, state)

    has_dates = await _send_available_dates(pid, tok, wa_phone, tenant_id, db)
    if not has_dates:
        await wa.send_text(
            pid, tok, wa_phone,
            "Simdilik onumuzdeki 7 gun icin musait randevu bulunmuyor.\n"
            "Lutfen daha sonra tekrar deneyin.",
        )
        await _reset_to_idle(pid, wa_phone, tenant_id, state.wa_name)


async def _handle_name_received(
    pid: str,
    tok: str,
    wa_phone: str,
    text: str,
    state: ConversationState,
    tenant: Tenant,
    db: AsyncSession,
) -> None:
    """Yeni kullanıcıdan gelen isim/soyisim metnini işler, kullanıcı oluşturur."""
    clean = " ".join(text.strip().split())  # Çoklu boşlukları tekleştir

    _VALID_NAME_RE = re.compile(r"^[a-zA-ZçğışöüÇĞIİÖŞÜ ]+$")
    words = clean.split()

    if not _VALID_NAME_RE.match(clean) or len(words) < 2 or len(words) > 3:
        await wa.send_text(
            pid, tok, wa_phone,
            "Gecersiz format.\n\n"
            "- En az 2, en fazla 3 kelime girin\n"
            "- Sadece harf kullanin\n\n"
            "Ornek: *Ahmet Yilmaz* veya *Ahmet Mehmet Yilmaz*",
        )
        return

    if len(words) == 2:
        first_name, last_name = words[0], words[1]
    else:  # 3 kelime: ilk 2'si isim, son'u soyisim
        first_name, last_name = f"{words[0]} {words[1]}", words[2]

    phone_with_plus = "+" + wa_phone
    try:
        normalized = normalize_tr_phone(phone_with_plus)
    except Exception:
        normalized = phone_with_plus

    user = User(
        tenant_id=tenant.id,
        phone=normalized,
        first_name=first_name,
        last_name=last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("WA yeni kullanıcı kayıt | tenant=%s phone=%s", tenant.id, normalized)

    state.user_id = str(user.id)
    state.step = STEP_DATE_SELECT
    await save_state(pid, wa_phone, state)

    await wa.send_text(pid, tok, wa_phone, f"Kaydınız oluşturuldu, merhaba {first_name}!")

    has_dates = await _send_available_dates(pid, tok, wa_phone, tenant.id, db)
    if not has_dates:
        await wa.send_text(
            pid, tok, wa_phone,
            "Simdilik onumuzdeki 7 gun icin musait randevu bulunmuyor.\n"
            "Lutfen daha sonra tekrar deneyin.",
        )
        await _reset_to_idle(pid, wa_phone, tenant.id, state.wa_name)


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
    state.slot_offset = 0
    await save_state(pid, wa_phone, state)

    has_times = await _send_available_times(pid, tok, wa_phone, tenant_id, selected_date, db, offset=0)
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
        await _reset_to_idle(pid, wa_phone, tenant.id, wa_name)
        await _send_main_menu(pid, tok, wa_phone, tenant.name)
        return

    try:
        user = await _get_or_create_user(db, tenant.id, wa_phone, wa_name)
    except Exception as exc:
        logger.error("Kullanıcı oluşturma hatası | error=%s", exc)
        await wa.send_text(pid, tok, wa_phone, "Bir hata olustu. Lutfen tekrar deneyin.")
        await _reset_to_idle(pid, wa_phone, tenant.id, wa_name)
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
        # Saatleri tekrar göster (aynı sayfada)
        state.step = STEP_TIME_SELECT
        state.selected_time = None
        await save_state(pid, wa_phone, state)
        await _send_available_times(pid, tok, wa_phone, tenant.id, selected_date, db, offset=state.slot_offset)
        return

    # Başarılı — tenant_id'yi koruyarak idle'a sıfırla
    await _reset_to_idle(pid, wa_phone, tenant.id, wa_name)
    date_label = _fmt_date(selected_date)
    site_url = f"https://{tenant.subdomain}.bbsoft.com.tr"
    success_msg = (
        f"Randevunuz olusturuldu!\n\n"
        f"Isletme: {tenant.name}\n"
        f"Misafir: {user.first_name} {user.last_name}\n"
        f"Gun:     {date_label}\n"
        f"Saat:    {state.selected_time}\n\n"
        f"Saat degisikligi, iptal ve diger hizmetler icin web sitemizi ziyaret edin:\n"
        f"🌐 {site_url}"
    )
    await wa.send_text(pid, tok, wa_phone, success_msg)
    logger.info("WA randevu oluşturuldu | booking_id=%s | user_id=%s", booking.id, user.id)


async def _handle_my_bookings(
    pid: str,
    tok: str,
    wa_phone: str,
    tenant_id: uuid.UUID,
    tenant: Tenant,
    db: AsyncSession,
) -> None:
    """Kullanıcının yaklaşan confirmed randevularını listeler."""
    phone_with_plus = "+" + wa_phone
    try:
        normalized = normalize_tr_phone(phone_with_plus)
    except Exception:
        normalized = phone_with_plus

    user_result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.phone.in_(phone_variants(normalized)),
        )
    )
    user = user_result.scalar_one_or_none()

    site_url = f"https://{tenant.subdomain}.bbsoft.com.tr"

    if user is None:
        await wa.send_text(
            pid, tok, wa_phone,
            "Sistemde kaydınız bulunmuyor.\n\n"
            "Randevu almak için 'Randevu Al' butonuna basın.",
        )
        return

    now = datetime.now(TZ)
    bookings_result = await db.execute(
        select(Booking)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.user_id == user.id,
            Booking.status == BookingStatus.confirmed,
            Booking.slot_time >= now,
        )
        .order_by(Booking.slot_time)
    )
    bookings = bookings_result.scalars().all()

    if not bookings:
        await wa.send_text(
            pid, tok, wa_phone,
            "Aktif randevunuz bulunmuyor.\n\n"
            "Randevu almak için 'Randevu Al' butonuna basın.",
        )
        return

    lines = ["📋 *Mevcut Randevularınız*\n"]
    for b in bookings:
        local = b.slot_time.astimezone(TZ)
        day_name = _TR_DAYS[local.weekday()]
        month_name = _TR_MONTHS[local.month]
        lines.append(f"📅 {day_name} {local.day} {month_name} - {local.strftime('%H:%M')}")

    lines.append(
        "\n\nSaat değiştirme, iptal etme ve benzeri işlemler için "
        "web sitemizi ziyaret edin:\n"
        f"🌐 {site_url}"
    )

    await wa.send_text(pid, tok, wa_phone, "\n".join(lines))
