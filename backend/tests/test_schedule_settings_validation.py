import pytest
from pydantic import ValidationError

from app.modules.schedule.schemas import BarberSettingsRequest, DayOverrideRequest


def _base_payload(slot_duration_minutes: int) -> dict:
    return {
        "slot_duration_minutes": slot_duration_minutes,
        "work_start_time": "09:00",
        "work_end_time": "19:00",
        "weekly_closed_days": [],
        "max_booking_days_ahead": 14,
    }


def test_schedule_settings_accepts_5_min_steps():
    payload = _base_payload(35)
    req = BarberSettingsRequest(**payload)
    assert req.slot_duration_minutes == 35


@pytest.mark.parametrize("invalid_duration", [0, 3, 121, 122])
def test_schedule_settings_rejects_out_of_range_or_non_step(invalid_duration: int):
    with pytest.raises(ValidationError):
        BarberSettingsRequest(**_base_payload(invalid_duration))


@pytest.mark.parametrize("valid_days", [1, 14, 60])
def test_schedule_settings_accepts_max_booking_days_ahead_in_range(valid_days: int):
    payload = _base_payload(30)
    payload["max_booking_days_ahead"] = valid_days
    req = BarberSettingsRequest(**payload)
    assert req.max_booking_days_ahead == valid_days


@pytest.mark.parametrize("invalid_days", [0, 61, 999])
def test_schedule_settings_rejects_invalid_max_booking_days_ahead(invalid_days: int):
    payload = _base_payload(30)
    payload["max_booking_days_ahead"] = invalid_days
    with pytest.raises(ValidationError):
        BarberSettingsRequest(**payload)


@pytest.mark.parametrize("valid_duration", [None, 5, 30, 120])
def test_day_override_accepts_valid_slot_duration(valid_duration: int | None):
    req = DayOverrideRequest(
        date="2026-04-01",
        is_closed=False,
        work_start_time="09:00",
        work_end_time="17:00",
        slot_duration_minutes=valid_duration,
    )
    assert req.slot_duration_minutes == valid_duration


@pytest.mark.parametrize("invalid_duration", [0, 3, 121, 122])
def test_day_override_rejects_invalid_slot_duration(invalid_duration: int):
    with pytest.raises(ValidationError):
        DayOverrideRequest(
            date="2026-04-01",
            is_closed=False,
            work_start_time="09:00",
            work_end_time="17:00",
            slot_duration_minutes=invalid_duration,
        )
