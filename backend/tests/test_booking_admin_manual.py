"""
test_booking_admin_manual.py - Admin manuel randevu akisina odakli testler.
"""

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from app.models.enums import BookingStatus
from app.modules.booking import router as booking_router
from app.modules.booking.schemas import AdminBookingCreateRequest

TZ = ZoneInfo("Europe/Istanbul")


@pytest.mark.asyncio
async def test_create_booking_admin_without_phone_uses_placeholder(monkeypatch):
    """
    Admin telefon girmeden manuel randevu olusturabilmeli.
    User.phone alani nullable olmadigi icin placeholder uretilerek kayit acilir.
    """
    tenant_id = uuid.uuid4()
    slot_time = datetime.now(TZ) + timedelta(days=1)

    # Telefon verilmedigi icin execute ile mevcut user aramasi yapilmamali.
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()

    async def _mock_flush():
        # Flush sonrasi user.id olusmus gibi davran.
        added_user = db.add.call_args.args[0]
        added_user.id = uuid.uuid4()

    db.flush = AsyncMock(side_effect=_mock_flush)
    db.rollback = AsyncMock()

    fake_booking = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        slot_time=slot_time,
        status=BookingStatus.confirmed,
        cancelled_by=None,
        created_at=datetime.now(TZ),
    )

    create_booking_admin_mock = AsyncMock(return_value=fake_booking)
    monkeypatch.setattr(booking_router.booking_service, "create_booking_admin", create_booking_admin_mock)

    body = AdminBookingCreateRequest(
        slot_time=slot_time,
        phone=None,
        first_name="Ali",
        last_name="Yilmaz",
    )
    admin = SimpleNamespace(tenant_id=tenant_id)

    await booking_router.create_booking_admin(body=body, db=db, admin=admin)

    # Telefon yoksa mevcut user aramasi yapilmamali.
    db.execute.assert_not_called()
    db.add.assert_called_once()
    added_user = db.add.call_args.args[0]
    assert added_user.phone.startswith("no-phone-")
    assert added_user.first_name == "Ali"
    assert added_user.last_name == "Yilmaz"

