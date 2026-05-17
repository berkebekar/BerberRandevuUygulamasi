"""WhatsApp bot feature settings helpers."""

from dataclasses import dataclass

from app.models.tenant import Tenant


def normalize_wa_phone(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def normalize_silent_numbers(values: list[str] | None) -> list[str]:
    seen: set[str] = set()
    clean: list[str] = []
    for value in values or []:
        normalized = normalize_wa_phone(value)
        if len(normalized) < 8 or normalized in seen:
            continue
        seen.add(normalized)
        clean.append(normalized)
    return clean


def _enabled(tenant: Tenant, field: str, default: bool = True) -> bool:
    return bool(getattr(tenant, field, default))


@dataclass(frozen=True)
class WhatsappFeatureSettings:
    bot_enabled: bool
    bot_superadmin_enabled: bool
    bot_effective_enabled: bool
    booking_enabled: bool
    booking_superadmin_enabled: bool
    booking_effective_enabled: bool
    reminder_enabled: bool
    reminder_superadmin_enabled: bool
    reminder_effective_enabled: bool
    cancellation_enabled: bool
    cancellation_superadmin_enabled: bool
    cancellation_effective_enabled: bool
    reschedule_enabled: bool
    reschedule_superadmin_enabled: bool
    reschedule_effective_enabled: bool
    silent_numbers: list[str]

    def as_dict(self) -> dict:
        return {
            "bot_enabled": self.bot_enabled,
            "bot_superadmin_enabled": self.bot_superadmin_enabled,
            "bot_effective_enabled": self.bot_effective_enabled,
            "booking_enabled": self.booking_enabled,
            "booking_superadmin_enabled": self.booking_superadmin_enabled,
            "booking_effective_enabled": self.booking_effective_enabled,
            "reminder_enabled": self.reminder_enabled,
            "reminder_superadmin_enabled": self.reminder_superadmin_enabled,
            "reminder_effective_enabled": self.reminder_effective_enabled,
            "cancellation_enabled": self.cancellation_enabled,
            "cancellation_superadmin_enabled": self.cancellation_superadmin_enabled,
            "cancellation_effective_enabled": self.cancellation_effective_enabled,
            "reschedule_enabled": self.reschedule_enabled,
            "reschedule_superadmin_enabled": self.reschedule_superadmin_enabled,
            "reschedule_effective_enabled": self.reschedule_effective_enabled,
            "silent_numbers": self.silent_numbers,
        }


def build_whatsapp_feature_settings(tenant: Tenant) -> WhatsappFeatureSettings:
    bot_enabled = _enabled(tenant, "whatsapp_bot_enabled")
    bot_superadmin_enabled = _enabled(tenant, "whatsapp_bot_superadmin_enabled")
    booking_enabled = _enabled(tenant, "whatsapp_booking_enabled")
    booking_superadmin_enabled = _enabled(tenant, "whatsapp_booking_superadmin_enabled")
    reminder_enabled = _enabled(tenant, "whatsapp_reminder_enabled")
    reminder_superadmin_enabled = _enabled(tenant, "whatsapp_reminder_superadmin_enabled")
    cancellation_enabled = _enabled(tenant, "whatsapp_cancellation_enabled")
    cancellation_superadmin_enabled = _enabled(tenant, "whatsapp_cancellation_superadmin_enabled")
    reschedule_enabled = _enabled(tenant, "whatsapp_reschedule_enabled")
    reschedule_superadmin_enabled = _enabled(tenant, "whatsapp_reschedule_superadmin_enabled")

    return WhatsappFeatureSettings(
        bot_enabled=bot_enabled,
        bot_superadmin_enabled=bot_superadmin_enabled,
        bot_effective_enabled=bot_enabled and bot_superadmin_enabled,
        booking_enabled=booking_enabled,
        booking_superadmin_enabled=booking_superadmin_enabled,
        booking_effective_enabled=booking_enabled and booking_superadmin_enabled,
        reminder_enabled=reminder_enabled,
        reminder_superadmin_enabled=reminder_superadmin_enabled,
        reminder_effective_enabled=reminder_enabled and reminder_superadmin_enabled,
        cancellation_enabled=cancellation_enabled,
        cancellation_superadmin_enabled=cancellation_superadmin_enabled,
        cancellation_effective_enabled=cancellation_enabled and cancellation_superadmin_enabled,
        reschedule_enabled=reschedule_enabled,
        reschedule_superadmin_enabled=reschedule_superadmin_enabled,
        reschedule_effective_enabled=reschedule_enabled and reschedule_superadmin_enabled,
        silent_numbers=normalize_silent_numbers(getattr(tenant, "whatsapp_silent_numbers", []) or []),
    )


def is_silent_contact(tenant: Tenant, wa_phone: str) -> bool:
    phone = normalize_wa_phone(wa_phone)
    if not phone:
        return False
    return phone in build_whatsapp_feature_settings(tenant).silent_numbers
