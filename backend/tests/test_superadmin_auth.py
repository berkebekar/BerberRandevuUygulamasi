"""
test_superadmin_auth.py - Super admin auth endpoint/dependency testleri.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.core.security import create_token, create_token_with_secret, decode_token_with_secret
from app.main import app


def _make_db_result(value) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_super_admin(
    username: str = "owner",
    password_hash: str = "",
    is_active: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        username=username,
        password_hash=password_hash,
        is_active=is_active,
        session_version=str(uuid.uuid4()),
    )


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_success_sets_superadmin_cookie():
    from app.core.security import hash_password

    super_admin = _make_super_admin(password_hash=hash_password("StrongPass123"))
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(super_admin))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/superadmin/auth/login",
            json={"username": "owner", "password": "StrongPass123"},
        )

    settings = get_settings()
    secret = settings.super_admin_session_secret or settings.secret_key
    assert response.status_code == 200
    assert response.json() == {"message": "login_successful"}
    assert settings.super_admin_cookie_name in response.cookies

    token = response.cookies[settings.super_admin_cookie_name]
    payload = decode_token_with_secret(token, secret)
    assert payload.get("role") == "superadmin"
    assert payload.get("sv")
    session.commit.assert_called_once()
    session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_login_invalid_credentials_401():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(None))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/superadmin/auth/login",
            json={"username": "owner", "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json() == {"error": "invalid_credentials"}


@pytest.mark.asyncio
async def test_login_inactive_super_admin_403():
    from app.core.security import hash_password

    super_admin = _make_super_admin(password_hash=hash_password("StrongPass123"), is_active=False)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(super_admin))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post(
            "/api/v1/superadmin/auth/login",
            json={"username": "owner", "password": "StrongPass123"},
        )

    assert response.status_code == 403
    assert response.json() == {"error": "super_admin_inactive"}


@pytest.mark.asyncio
async def test_logout_success_rotates_session_and_deletes_cookie():
    settings = get_settings()
    secret = settings.super_admin_session_secret or settings.secret_key
    super_admin = _make_super_admin()
    token = create_token_with_secret(
        {"sub": str(super_admin.id), "role": "superadmin", "sv": super_admin.session_version},
        expires_minutes=30,
        secret_key=secret,
    )

    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(super_admin))
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        client.cookies.set(settings.super_admin_cookie_name, token)
        response = await client.post("/api/v1/superadmin/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "logged_out"}
    session.commit.assert_called_once()
    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any(settings.super_admin_cookie_name in v for v in set_cookie_headers)


@pytest.mark.asyncio
async def test_logout_idempotent_without_cookie_200():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(None))
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.post("/api/v1/superadmin/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"message": "logged_out"}
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_dependency_wrong_role_forbidden():
    token = create_token({"sub": str(uuid.uuid4()), "role": "admin", "sv": str(uuid.uuid4())}, expires_minutes=30)
    request = MagicMock()
    request.state = SimpleNamespace()
    session = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await get_current_super_admin(request=request, superadmin_session=token, db=session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_dependency_session_revoked_401():
    settings = get_settings()
    secret = settings.super_admin_session_secret or settings.secret_key
    super_admin = _make_super_admin()
    token = create_token_with_secret(
        {"sub": str(super_admin.id), "role": "superadmin", "sv": str(uuid.uuid4())},
        expires_minutes=30,
        secret_key=secret,
    )
    request = MagicMock()
    request.state = SimpleNamespace()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(super_admin))

    with pytest.raises(Exception) as exc_info:
        await get_current_super_admin(request=request, superadmin_session=token, db=session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {"error": "session_revoked"}


@pytest.mark.asyncio
async def test_dependency_super_admin_not_found_401():
    settings = get_settings()
    secret = settings.super_admin_session_secret or settings.secret_key
    token = create_token_with_secret(
        {"sub": str(uuid.uuid4()), "role": "superadmin", "sv": str(uuid.uuid4())},
        expires_minutes=30,
        secret_key=secret,
    )
    request = MagicMock()
    request.state = SimpleNamespace()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(None))

    with pytest.raises(Exception) as exc_info:
        await get_current_super_admin(request=request, superadmin_session=token, db=session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == {"error": "super_admin_not_found"}
