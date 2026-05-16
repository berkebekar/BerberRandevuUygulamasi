import uuid
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.modules.whatsapp import handlers
from app.modules.whatsapp.state import STEP_SAME_DAY_CONFIRM, ConversationState


@pytest.mark.asyncio
async def test_whatsapp_same_day_confirmation_sets_confirm_flag(monkeypatch):
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        name="Berke Bekar",
        subdomain="berke",
    )
    user = SimpleNamespace(id=uuid.uuid4(), first_name="Mehmet", last_name="Yilmaz")
    state = ConversationState(
        tenant_id=str(tenant.id),
        wa_name="Mehmet",
        selected_date=date.today().isoformat(),
        selected_time="10:00",
    )
    sent_texts: list[str] = []
    confirm_flags: list[bool] = []

    async def fake_get_or_create_user(db, tenant_id, wa_phone, wa_name):
        return user

    async def fake_create_booking(db, tenant_id, user_id, slot_dt, confirm_additional_same_day, source):
        confirm_flags.append(confirm_additional_same_day)
        return SimpleNamespace(id=uuid.uuid4())

    async def fake_reset_to_idle(pid, wa_phone, tenant_id, wa_name):
        return None

    async def fake_send_text(pid, tok, wa_phone, text):
        sent_texts.append(text)
        return True

    monkeypatch.setattr(handlers, "_get_or_create_user", fake_get_or_create_user)
    monkeypatch.setattr(handlers.booking_service, "create_booking", fake_create_booking)
    monkeypatch.setattr(handlers, "_reset_to_idle", fake_reset_to_idle)
    monkeypatch.setattr(handlers.wa, "send_text", fake_send_text)

    await handlers._handle_booking_confirm(
        "phone-id",
        "token",
        "905551112233",
        "Mehmet",
        state,
        tenant,
        db=object(),
        confirm_same_day=True,
    )

    assert confirm_flags == [True]
    assert sent_texts
    assert "/menu" in sent_texts[-1]


@pytest.mark.asyncio
async def test_whatsapp_same_day_required_moves_to_confirmation_step(monkeypatch):
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        name="Berke Bekar",
        subdomain="berke",
    )
    user = SimpleNamespace(id=uuid.uuid4(), first_name="Mehmet", last_name="Yilmaz")
    state = ConversationState(
        tenant_id=str(tenant.id),
        wa_name="Mehmet",
        selected_date=date.today().isoformat(),
        selected_time="10:00",
    )
    sent_buttons: list[dict] = []
    saved_states: list[ConversationState] = []

    async def fake_get_or_create_user(db, tenant_id, wa_phone, wa_name):
        return user

    async def fake_create_booking(*args, **kwargs):
        raise HTTPException(409, {"error": "additional_booking_confirmation_required"})

    async def fake_save_state(pid, wa_phone, next_state):
        saved_states.append(next_state)

    async def fake_send_buttons(pid, tok, wa_phone, body, buttons, footer=""):
        sent_buttons.append({"body": body, "buttons": buttons})
        return True

    monkeypatch.setattr(handlers, "_get_or_create_user", fake_get_or_create_user)
    monkeypatch.setattr(handlers.booking_service, "create_booking", fake_create_booking)
    monkeypatch.setattr(handlers, "save_state", fake_save_state)
    monkeypatch.setattr(handlers.wa, "send_buttons", fake_send_buttons)

    await handlers._handle_booking_confirm(
        "phone-id",
        "token",
        "905551112233",
        "Mehmet",
        state,
        tenant,
        db=object(),
    )

    assert state.step == STEP_SAME_DAY_CONFIRM
    assert saved_states[-1].step == STEP_SAME_DAY_CONFIRM
    assert [button.id for button in sent_buttons[-1]["buttons"]] == [
        "confirm_additional_yes",
        "cancel_booking",
    ]
