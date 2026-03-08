import pytest
from pydantic import ValidationError

from app.modules.schedule.schemas import BarberSettingsRequest


def _base_payload(slot_duration_minutes: int) -> dict:
    return {
        "slot_duration_minutes": slot_duration_minutes,
        "work_start_time": "09:00",
        "work_end_time": "19:00",
        "weekly_closed_days": [],
    }


def test_schedule_settings_accepts_5_min_steps():
    payload = _base_payload(35)
    req = BarberSettingsRequest(**payload)
    assert req.slot_duration_minutes == 35


@pytest.mark.parametrize("invalid_duration", [0, 3, 121, 122])
def test_schedule_settings_rejects_out_of_range_or_non_step(invalid_duration: int):
    with pytest.raises(ValidationError):
        BarberSettingsRequest(**_base_payload(invalid_duration))
