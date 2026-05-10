"""test_tenant_info.py - Public tenant info endpoint tests."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.tenant.router import get_tenant_info


def _make_db_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_tenant_info_returns_contact_details():
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        name="Acme Barber",
        first_name=None,
        last_name=None,
        address="Acme Mah. Randevu Sok. No: 1",
    )
    admin = SimpleNamespace(phone="+905551112233")
    request = MagicMock()
    request.state = SimpleNamespace(tenant_id=tenant_id)
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(tenant),
            _make_db_result(admin),
        ]
    )

    result = await get_tenant_info(request=request, db=session)

    assert result.name == "Acme Barber"
    assert result.phone == "+905551112233"
    assert result.address == "Acme Mah. Randevu Sok. No: 1"
