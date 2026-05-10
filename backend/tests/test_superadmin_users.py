"""
test_superadmin_users.py - Super admin user management testleri.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.core.security import create_token_with_secret, decode_token, hash_password
from app.main import app
from app.models.activity_log import ActivityLog
from app.models.enums import OTPRole, UserStatus
from app.modules.auth import service as auth_service
from app.modules.booking.router import create_booking as create_booking_endpoint
from app.modules.superadmin.user_service import hard_delete_user


def _make_db_result(*, scalar_or_none=None, scalar_value=None, all_value=None, one_or_none_value=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_or_none
    result.scalar_one.return_value = scalar_value
    result.all.return_value = all_value if all_value is not None else []
    result.one_or_none.return_value = one_or_none_value
    return result


def _override_super_admin():
    return SimpleNamespace(
        id=uuid.uuid4(),
        username="owner",
        is_active=True,
        session_version=str(uuid.uuid4()),
    )


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_superadmin_users_auth_missing_cookie_returns_401():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/users")

    assert response.status_code == 401
    assert response.json() == {"error": "not_authenticated"}


@pytest.mark.asyncio
async def test_superadmin_users_auth_wrong_role_returns_403():
    settings = get_settings()
    secret = settings.super_admin_session_secret or settings.secret_key
    token = create_token_with_secret(
        {"sub": str(uuid.uuid4()), "role": "admin", "sv": str(uuid.uuid4())},
        expires_minutes=30,
        secret_key=secret,
    )

    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        client.cookies.set(settings.super_admin_cookie_name, token)
        response = await client.get("/api/v1/superadmin/users")

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_superadmin_users_list_success():
    tenant = SimpleNamespace(id=uuid.uuid4(), subdomain="acme", name="Acme")
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        phone="+905551112233",
        first_name="Ali",
        last_name="Veli",
        status=UserStatus.active,
        is_blocked=False,
        created_at=datetime.now(timezone.utc),
    )
    rows_result = _make_db_result(all_value=[(user, tenant, 3, datetime.now(timezone.utc))])
    total_result = _make_db_result(scalar_value=1)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[total_result, rows_result])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/users?page=1&page_size=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["tenant"]["subdomain"] == "acme"
    assert payload["items"][0]["booking_count"] == 3


@pytest.mark.asyncio
async def test_superadmin_user_detail_not_found_404():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(one_or_none_value=None)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get(f"/api/v1/superadmin/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"error": "user_not_found"}


@pytest.mark.asyncio
async def test_superadmin_user_block_deleted_returns_409():
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status=UserStatus.deleted,
        is_blocked=False,
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=user)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.put(
            f"/api/v1/superadmin/users/{user.id}/block",
            json={"reason": "abuse"},
        )

    assert response.status_code == 409
    assert response.json() == {"error": "user_deleted"}


@pytest.mark.asyncio
async def test_hard_delete_user_removes_related_records_and_logs():
    super_admin = _override_super_admin()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        phone="+905551112233",
        status=UserStatus.deleted,
        is_blocked=False,
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=user), None, None, None])
    added_objects: list[object] = []
    session.add = MagicMock(side_effect=added_objects.append)
    session.commit = AsyncMock()

    result = await hard_delete_user(session, super_admin, user.id)

    assert result.id == user.id
    assert result.message == "user_hard_deleted"
    assert session.execute.await_count == 4
    assert session.commit.await_count == 1
    assert len(added_objects) == 1
    assert isinstance(added_objects[0], ActivityLog)
    assert added_objects[0].action_type == "user_hard_deleted"
    assert added_objects[0].entity_id == str(user.id)


@pytest.mark.asyncio
async def test_superadmin_user_impersonate_sets_user_cookie():
    super_admin = _override_super_admin()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        phone="+905551112233",
        first_name="Ali",
        last_name="Veli",
        status=UserStatus.active,
        is_blocked=False,
        session_version=str(uuid.uuid4()),
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=user)])
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = lambda: super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(f"/api/v1/superadmin/users/{user.id}/impersonate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "impersonation_started"
    assert payload["expires_in_seconds"] == 3600
    assert "user_session" in response.cookies
    token_payload = decode_token(response.cookies["user_session"])
    assert token_payload.get("role") == "user"
    assert token_payload.get("imp") is True
    assert token_payload.get("imp_by") == str(super_admin.id)
    assert token_payload.get("imp_tenant") == str(user.tenant_id)


@pytest.mark.asyncio
async def test_superadmin_exit_clears_user_impersonation_cookie():
    super_admin = _override_super_admin()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = create_token_with_secret(
        {
            "sub": str(user_id),
            "role": "user",
            "sv": str(uuid.uuid4()),
            "imp": True,
            "imp_by": str(super_admin.id),
            "imp_tenant": str(tenant_id),
            "imp_exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        },
        expires_minutes=60,
        secret_key=get_settings().secret_key,
    )
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = lambda: super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        client.cookies.set("user_session", token)
        response = await client.post("/api/v1/superadmin/impersonate/exit")

    assert response.status_code == 200
    assert response.json() == {"message": "impersonation_ended"}
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("user_session=" in v for v in set_cookie_headers)
    assert all("admin_session=" not in v for v in set_cookie_headers)


@pytest.mark.asyncio
async def test_verify_otp_deleted_user_rejected():
    tenant_id = uuid.uuid4()
    phone = "+905551112233"
    otp_record = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        phone=phone,
        code_hash=hash_password("123456"),
        role=OTPRole.user,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_used=False,
        attempt_count=0,
    )
    deleted_user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        phone=phone,
        first_name="Deleted",
        last_name="User",
        status=UserStatus.deleted,
        is_blocked=False,
        session_version=str(uuid.uuid4()),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(scalar_or_none=otp_record),
            _make_db_result(scalar_or_none=deleted_user),
        ]
    )
    session.commit = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.verify_otp(session, tenant_id=tenant_id, phone=phone, code="123456")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {"error": "user_deleted"}


@pytest.mark.asyncio
async def test_booking_create_blocked_user_rejected():
    slot_time = datetime.now(timezone.utc) + timedelta(days=1)
    body = SimpleNamespace(slot_time=slot_time, confirm_additional_same_day=False)
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status=UserStatus.blocked,
        is_blocked=True,
    )
    session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await create_booking_endpoint(body=body, db=session, user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {"error": "user_blocked"}
