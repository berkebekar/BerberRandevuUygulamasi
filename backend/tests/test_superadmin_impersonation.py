"""
test_superadmin_impersonation.py - Super admin tenant impersonation testleri.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.core.security import create_token, decode_token
from app.main import app
from app.models.enums import TenantStatus


def _make_db_result(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_super_admin() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        username="owner",
        is_active=True,
        session_version=str(uuid.uuid4()),
    )


def _make_admin(tenant_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="admin@acme.com",
        phone="+905551112233",
        session_version=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_impersonate_requires_superadmin_auth():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(f"/api/v1/superadmin/tenants/{uuid.uuid4()}/impersonate")

    assert response.status_code == 401
    assert response.json() == {"error": "not_authenticated"}


@pytest.mark.asyncio
async def test_impersonate_tenant_not_found_404():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(None)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _make_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(f"/api/v1/superadmin/tenants/{uuid.uuid4()}/impersonate")

    assert response.status_code == 404
    assert response.json() == {"error": "tenant_not_found"}


@pytest.mark.asyncio
async def test_impersonate_deleted_tenant_409():
    tenant = SimpleNamespace(id=uuid.uuid4(), status=TenantStatus.deleted)
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(tenant)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _make_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(f"/api/v1/superadmin/tenants/{tenant.id}/impersonate")

    assert response.status_code == 409
    assert response.json() == {"error": "tenant_deleted"}


@pytest.mark.asyncio
async def test_impersonate_admin_not_found_404():
    tenant = SimpleNamespace(id=uuid.uuid4(), status=TenantStatus.active)
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(tenant), _make_db_result(None)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _make_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(f"/api/v1/superadmin/tenants/{tenant.id}/impersonate")

    assert response.status_code == 404
    assert response.json() == {"error": "admin_not_found"}


@pytest.mark.asyncio
async def test_impersonate_success_sets_cookie_and_logs():
    super_admin = _make_super_admin()
    tenant = SimpleNamespace(id=uuid.uuid4(), status=TenantStatus.active)
    admin = _make_admin(tenant.id)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(tenant), _make_db_result(admin)])
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = lambda: super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(f"/api/v1/superadmin/tenants/{tenant.id}/impersonate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "impersonation_started"
    assert payload["expires_in_seconds"] == 3600
    assert "admin_session" in response.cookies

    token_payload = decode_token(response.cookies["admin_session"])
    assert token_payload.get("imp") is True
    assert token_payload.get("imp_by") == str(super_admin.id)
    assert token_payload.get("imp_tenant") == str(tenant.id)
    assert token_payload.get("role") == "admin"
    assert token_payload.get("sub") == str(admin.id)
    assert token_payload.get("imp_exp")
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_exit_clears_admin_cookie_and_logs():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    super_admin = _make_super_admin()
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    token = create_token(
        {
            "sub": str(admin_id),
            "role": "admin",
            "sv": str(uuid.uuid4()),
            "imp": True,
            "imp_by": str(super_admin.id),
            "imp_tenant": str(tenant_id),
            "imp_exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        },
        expires_minutes=60,
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = lambda: super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        client.cookies.set("admin_session", token)
        response = await client.post("/api/v1/superadmin/impersonate/exit")

    assert response.status_code == 200
    assert response.json() == {"message": "impersonation_ended"}
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("admin_session=" in v for v in set_cookie_headers)
    assert all("superadmin_session=" not in v for v in set_cookie_headers)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_admin_impersonation_allows_same_tenant():
    tenant_id = uuid.uuid4()
    admin = _make_admin(tenant_id)
    token = create_token(
        {
            "sub": str(admin.id),
            "role": "admin",
            "sv": admin.session_version,
            "imp": True,
            "imp_by": str(uuid.uuid4()),
            "imp_tenant": str(tenant_id),
            "imp_exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        expires_minutes=60,
    )
    request = MagicMock()
    request.state = SimpleNamespace(tenant_id=tenant_id)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(admin))

    result = await get_current_admin(request=request, admin_session=token, db=session)
    assert result.id == admin.id
    assert request.state.is_impersonated is True
    assert request.state.impersonated_by_super_admin_id is not None


@pytest.mark.asyncio
async def test_get_current_admin_impersonation_rejects_other_tenant():
    tenant_id = uuid.uuid4()
    token = create_token(
        {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "sv": str(uuid.uuid4()),
            "imp": True,
            "imp_by": str(uuid.uuid4()),
            "imp_tenant": str(uuid.uuid4()),
            "imp_exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
        },
        expires_minutes=60,
    )
    request = MagicMock()
    request.state = SimpleNamespace(tenant_id=tenant_id)
    session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(request=request, admin_session=token, db=session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_get_current_admin_impersonation_ttl_expired_401():
    tenant_id = uuid.uuid4()
    token = create_token(
        {
            "sub": str(uuid.uuid4()),
            "role": "admin",
            "sv": str(uuid.uuid4()),
            "imp": True,
            "imp_by": str(uuid.uuid4()),
            "imp_tenant": str(tenant_id),
            "imp_exp": int((datetime.now(timezone.utc) - timedelta(seconds=5)).timestamp()),
        },
        expires_minutes=60,
    )
    request = MagicMock()
    request.state = SimpleNamespace(tenant_id=tenant_id)
    session = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(request=request, admin_session=token, db=session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {"error": "invalid_token"}
