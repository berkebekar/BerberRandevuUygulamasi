"""
test_error_logging_handlers.py - Global error logging handler davranislari.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.main import app
from app.models.enums import UserStatus


def _db_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _override_super_admin():
    return SimpleNamespace(
        id=uuid.uuid4(),
        username="owner",
        is_active=True,
        session_version=str(uuid.uuid4()),
    )


@pytest.fixture(autouse=True)
def reset_dependency_overrides(monkeypatch):
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    monkeypatch.undo()


@pytest.mark.asyncio
async def test_http_401_triggers_error_log(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(main_module, "log_error_best_effort", log_mock)
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/monitoring/health")

    assert response.status_code == 401
    assert log_mock.await_count == 1
    assert log_mock.await_args.kwargs["status_code"] == 401


@pytest.mark.asyncio
async def test_http_409_triggers_error_log(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(main_module, "log_error_best_effort", log_mock)
    deleted_user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status=UserStatus.deleted,
        is_blocked=False,
        created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_db_result(deleted_user))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.put(
            f"/api/v1/superadmin/users/{deleted_user.id}/block",
            json={"reason": "policy"},
        )

    assert response.status_code == 409
    assert log_mock.await_count == 1
    assert log_mock.await_args.kwargs["status_code"] == 409


@pytest.mark.asyncio
async def test_http_404_passed_to_logging_helper(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(main_module, "log_error_best_effort", log_mock)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_db_result(None))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get(f"/api/v1/superadmin/logs/errors/{uuid.uuid4()}")

    assert response.status_code == 404
    assert log_mock.await_count == 1
    assert log_mock.await_args.kwargs["status_code"] == 404


@pytest.mark.asyncio
async def test_http_500_triggers_error_log(monkeypatch):
    log_mock = AsyncMock()
    monkeypatch.setattr(main_module, "log_error_best_effort", log_mock)

    if not any(getattr(route, "path", "") == "/http-500-test" for route in app.routes):
        @app.get("/http-500-test")
        async def http_500_test():
            raise HTTPException(500, {"error": "server_error"})

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        response = await client.get("/http-500-test")

    assert response.status_code == 500
    assert log_mock.await_count == 1
    assert log_mock.await_args.kwargs["status_code"] == 500


@pytest.mark.asyncio
async def test_log_error_best_effort_masks_sensitive_data():
    from starlette.requests import Request

    from app.core.error_logging import _build_masked_request_meta

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/test",
        "headers": [
            (b"authorization", b"Bearer abc"),
            (b"cookie", b"user_session=secret"),
            (b"content-type", b"application/json"),
        ],
        "query_string": b"a=1",
        "client": ("127.0.0.1", 1234),
    }

    async def receive():
        return {
            "type": "http.request",
            "body": b'{"password":"x","otp":"123456","profile":{"name":"Ali"}}',
            "more_body": False,
        }

    request = Request(scope, receive)
    meta = await _build_masked_request_meta(request)
    assert meta["headers"]["authorization"] == "***"
    assert meta["headers"]["cookie"] == "***"
    assert meta["body"]["password"] == "***"
    assert meta["body"]["otp"] == "***"
    assert meta["body"]["profile"]["name"] == "Ali"


def test_should_log_error_status_only_critical_4xx_and_5xx():
    from app.core.error_logging import should_log_error_status

    assert should_log_error_status(500) is True
    assert should_log_error_status(401) is True
    assert should_log_error_status(403) is True
    assert should_log_error_status(409) is True
    assert should_log_error_status(404) is False
    assert should_log_error_status(422) is False
