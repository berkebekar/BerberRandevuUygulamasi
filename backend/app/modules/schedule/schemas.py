"""
schedule/schemas.py â€” Schedule modÃ¼lÃ¼ Pydantic ÅŸemalarÄ±.

Slotlarla ilgili tÃ¼m request/response modellerini tanÄ±mlar:
- GÃ¼nlÃ¼k ve haftalÄ±k slot listeleri (okuma)
- Berber ayarlarÄ± (Ã§alÄ±ÅŸma saatleri, slot sÃ¼resi)
- GÃ¼nlÃ¼k override (tatil veya farklÄ± saatler)
- Slot bloklama
"""

import enum
import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, field_validator, model_validator


# â”€â”€â”€ Slot Durumu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SlotStatus(str, enum.Enum):
    """
    Bir slotun durumu (CURSOR_PROMPTS ADIM 6).
    available : randevu alÄ±nabilir
    booked    : zaten confirmed randevu var
    blocked   : admin tarafÄ±ndan kapatÄ±lmÄ±ÅŸ
    past      : zaman geÃ§miÅŸ, artÄ±k seÃ§ilemez
    """
    available = "available"
    booked    = "booked"
    blocked   = "blocked"
    past      = "past"


# â”€â”€â”€ Slot Listesi YanÄ±tlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class SlotItem(BaseModel):
    """Tek bir randevu slotu."""
    time: str        # "09:00" formatÄ±nda saat string'i â€” ekranda gÃ¶stermek iÃ§in
    datetime: datetime  # ISO 8601 + timezone ("+03:00") â€” API kullanÄ±cÄ±sÄ± iÃ§in kesin zaman
    end_datetime: datetime  # Slot bitiÅŸ zamanÄ± (baÅŸlangÄ±Ã§ + slot sÃ¼resi)
    status: SlotStatus


class DaySlots(BaseModel):
    """Bir gÃ¼ne ait tÃ¼m slotlar."""
    date: date
    is_closed: bool   # True ise o gÃ¼n tamamen kapalÄ±, slots listesi boÅŸtur
    max_booking_days_ahead: int = 14
    slots: list[SlotItem]


class WeekSlots(BaseModel):
    """7 gÃ¼nlÃ¼k slot listesi (GET /slots/week yanÄ±tÄ±)."""
    week: list[DaySlots]


# â”€â”€â”€ Admin: Berber AyarlarÄ± â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BarberSettingsResponse(BaseModel):
    """Berber Ã§alÄ±ÅŸma ayarlarÄ± okuma yanÄ±tÄ±."""
    slot_duration_minutes: int
    work_start_time: time
    work_end_time: time
    weekly_closed_days: list[int]
    max_booking_days_ahead: int = 14


class BarberSettingsRequest(BaseModel):
    """
    Berber Ã§alÄ±ÅŸma ayarlarÄ± gÃ¼ncelleme isteÄŸi.
    slot_duration_minutes: 5-120 dakika araliginda ve 5'in kati olabilir.
    """
    slot_duration_minutes: int
    work_start_time: time
    work_end_time: time
    weekly_closed_days: list[int] = []
    max_booking_days_ahead: int = 14

    @field_validator("slot_duration_minutes")
    @classmethod
    def valid_duration(cls, v: int) -> int:
        """Randevu suresi 5-120 dakika araliginda ve 5'in kati olmalidir."""
        if v < 5 or v > 120 or v % 5 != 0:
            raise ValueError("Randevu suresi 5 ile 120 dakika arasinda ve 5'in kati olmalidir")
        return v

    @field_validator("work_end_time")
    @classmethod
    def end_after_start(cls, v: time, info) -> time:
        """BitiÅŸ saati baÅŸlangÄ±Ã§tan bÃ¼yÃ¼k olmalÄ±dÄ±r."""
        start = info.data.get("work_start_time")
        if start and v == time(0, 0) and start != time(0, 0):
            return v
        if start and v <= start:
            raise ValueError("BitiÅŸ saati baÅŸlangÄ±Ã§ saatinden bÃ¼yÃ¼k olmalÄ±dÄ±r")
        return v

    @field_validator("weekly_closed_days")
    @classmethod
    def valid_weekly_days(cls, v: list[int]) -> list[int]:
        """HaftanÄ±n gÃ¼nleri 0 ile 6 arasÄ±nda olmalÄ±dÄ±r."""
        if any(day < 0 or day > 6 for day in v):
            raise ValueError("HaftanÄ±n gÃ¼nleri 0 ile 6 arasÄ±nda olmalÄ±dÄ±r")
        return sorted(set(v))

    @field_validator("max_booking_days_ahead")
    @classmethod
    def valid_max_booking_days(cls, v: int) -> int:
        """Ileri tarih limiti 1-60 gun araliginda olmalidir."""
        if v < 1 or v > 60:
            raise ValueError("Ileri tarih limiti 1 ile 60 gun arasinda olmalidir")
        return v


# â”€â”€â”€ Admin: GÃ¼nlÃ¼k Override â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class DayOverrideRequest(BaseModel):
    """
    Belirli bir gÃ¼ne Ã¶zel Ã§alÄ±ÅŸma saatleri veya tatil ayarÄ±.
    is_closed=True ise work_start_time ve work_end_time dikkate alÄ±nmaz.
    is_closed=False ise her iki saat alanÄ± zorunludur.
    """
    date: date
    is_closed: bool
    work_start_time: time | None = None
    work_end_time: time | None   = None
    slot_duration_minutes: int | None = None

    @model_validator(mode="after")
    def times_required_when_open(self) -> "DayOverrideRequest":
        """
        GÃ¼n aÃ§Ä±k (is_closed=False) ise baÅŸlangÄ±Ã§ ve bitiÅŸ saatleri zorunludur.
        AyrÄ±ca bitiÅŸ saati baÅŸlangÄ±Ã§tan bÃ¼yÃ¼k olmalÄ±dÄ±r.
        is_closed=True ise saatler yok sayÄ±lÄ±r â€” gÃ¼n tamamen kapalÄ±.
        """
        if not self.is_closed:
            if self.work_start_time is None or self.work_end_time is None:
                raise ValueError(
                    "is_closed=False ise work_start_time ve work_end_time zorunludur"
                )
            if self.work_end_time == time(0, 0) and self.work_start_time != time(0, 0):
                return self
            if self.work_end_time <= self.work_start_time:
                raise ValueError("BitiÅŸ saati baÅŸlangÄ±Ã§ saatinden bÃ¼yÃ¼k olmalÄ±dÄ±r")
        return self

    @field_validator("slot_duration_minutes")
    @classmethod
    def valid_override_duration(cls, v: int | None) -> int | None:
        """Ozel gun slot suresi verilirse 5-120 arasinda ve 5'in kati olmalidir."""
        if v is None:
            return None
        if v < 5 or v > 120 or v % 5 != 0:
            raise ValueError("Ozel gun slot suresi 5 ile 120 dakika arasinda ve 5'in kati olmalidir")
        return v


class DayOverrideResponse(BaseModel):
    """
    Belirli bir gun icin ozel ayar kaydi.
    Kayit yoksa endpoint null doner.
    """
    date: date
    is_closed: bool
    work_start_time: time | None = None
    work_end_time: time | None = None
    slot_duration_minutes: int | None = None


# â”€â”€â”€ Admin: Slot Bloklama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BlockSlotRequest(BaseModel):
    """
    Bir slotu bloklamak iÃ§in istek.
    slot_datetime: bloklanacak slotun tam tarih-saat deÄŸeri (timezone dahil).
    reason: isteÄŸe baÄŸlÄ± aÃ§Ä±klama (Ã¶rn: "Ã–ÄŸle molasÄ±").
    """
    slot_datetime: datetime
    reason: str | None = None

    @field_validator("slot_datetime")
    @classmethod
    def slot_datetime_must_be_timezone_aware(cls, v: datetime) -> datetime:
        """Bloklanacak zaman timezone bilgisi icermelidir (ornek: +03:00)."""
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("slot_datetime timezone bilgisi icermelidir")
        return v


class BlockSlotResponse(BaseModel):
    """Slot bloklama baÅŸarÄ± yanÄ±tÄ±."""
    id: uuid.UUID   # SlotBlock kaydÄ±nÄ±n UUID'si â€” diÄŸer response modelleriyle tutarlÄ±
    blocked_at: datetime
    reason: str | None

# ---------------------------------------------------------
# Admin: Bloklu slot listesi
# ---------------------------------------------------------

class BlockedSlotItem(BaseModel):
    """
    Admin icin tek bir bloklu slot kaydi.
    Bu kayit, "slotu ac" islemi icin block_id icerir.
    """
    id: uuid.UUID
    blocked_at: datetime
    reason: str | None


class BlockedSlotsResponse(BaseModel):
    """
    Belirli bir gun icin bloklu slot listesi.
    Admin dashboard'da bloklu slotlari acmak icin kullanilir.
    """
    date: date
    blocks: list[BlockedSlotItem]

