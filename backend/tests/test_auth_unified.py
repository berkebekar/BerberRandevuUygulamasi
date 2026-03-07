"""
test_auth_unified.py - Tek giris auth endpoint'leri icin testler.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.security import decode_token, hash_password
from app.main import app
from app.modules.auth.router import get_tenant_id

TEST_TENANT_ID = uuid.uuid4()


def _make_db_result(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_admin(phone: str = "+905559876543") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        email="admin@test.com",
        phone=phone,
        password_hash=hash_password("sifre1234"),
        session_version=str(uuid.uuid4()),
    )


def _make_user(phone: str = "+905551234567") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        phone=phone,
        first_name="Test",
        last_name="User",
        session_version=str(uuid.uuid4()),
    )


def _make_otp_record(phone: str, role: str, code: str = "123456") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TEST_TENANT_ID,
        phone=phone,
        code_hash=hash_password(code),
        role=role,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_used=False,
        attempt_count=0,
    )


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def _override_tenant_id():
    return TEST_TENANT_ID


@pytest.mark.asyncio
async def test_unified_verify_admin_phone_sets_admin_cookie_and_next_admin():
    admin = _make_admin()
    admin_otp = _make_otp_record(phone=admin.phone, role="admin")

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(admin),       # unified endpoint: admin var mi?
            _make_db_result(admin_otp),   # verify_admin_otp: OTP kaydi
            _make_db_result(admin),       # verify_admin_otp: admin kaydi
        ]
    )
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": admin.phone, "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json() == {"next": "admin", "registration_token": None}
    assert "admin_session" in response.cookies
    payload = decode_token(response.cookies["admin_session"])
    assert payload.get("role") == "admin"


@pytest.mark.asyncio
async def test_unified_verify_user_phone_sets_user_cookie_and_next_user():
    user = _make_user()
    user_otp = _make_otp_record(phone=user.phone, role="user")

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(None),       # unified endpoint: admin var mi?
            _make_db_result(user_otp),   # verify_otp: OTP kaydi
            _make_db_result(user),       # verify_otp: user kaydi
        ]
    )
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": user.phone, "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json() == {"next": "user", "registration_token": None}
    assert "user_session" in response.cookies
    payload = decode_token(response.cookies["user_session"])
    assert payload.get("role") == "user"


@pytest.mark.asyncio
async def test_unified_verify_admin_legacy_phone_format_matches():
    admin = _make_admin(phone="905559876543")
    admin_otp = _make_otp_record(phone="+905559876543", role="admin")

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(admin),       # unified endpoint: admin var mi?
            _make_db_result(admin_otp),   # verify_admin_otp: OTP kaydi
            _make_db_result(admin),       # verify_admin_otp: admin kaydi
        ]
    )
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = _override_tenant_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "+905559876543", "code": "123456"},
        )

    assert response.status_code == 200
    assert response.json()["next"] == "admin"
