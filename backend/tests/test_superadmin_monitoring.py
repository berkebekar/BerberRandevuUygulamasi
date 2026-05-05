"""
test_superadmin_monitoring.py - Super admin monitoring/logging endpoint testleri.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.core.security import create_token_with_secret
from app.main import app
from app.modules.superadmin import monitoring_service
from app.modules.superadmin.monitoring_schemas import HostResourceUsage


def _db_result(*, scalar_or_none=None, scalar_value=None, all_value=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_or_none
    result.scalar_one.return_value = scalar_value
    result.all.return_value = all_value if all_value is not None else []
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = all_value if all_value is not None else []
    result.scalars.return_value = scalars_mock
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
async def test_monitoring_auth_missing_cookie_returns_401():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/monitoring/health")

    assert response.status_code == 401
    assert response.json() == {"error": "not_authenticated"}


@pytest.mark.asyncio
async def test_monitoring_auth_wrong_role_returns_403():
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
        response = await client.get("/api/v1/superadmin/monitoring/health")

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_monitoring_health_returns_backend_db_frontend():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _db_result(),  # SELECT 1
        ]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    original_frontend_check = monitoring_service._check_frontend_health
    original_host_resources = monitoring_service._collect_host_resources
    monitoring_service._check_frontend_health = AsyncMock(
        return_value=("operational", 120.0, datetime.now(timezone.utc), {"url": "https://example.com"})
    )
    monitoring_service._collect_host_resources = AsyncMock(
        return_value=HostResourceUsage(
            cpu_percent=25.0,
            ram_percent=50.0,
            disk_percent=40.0,
            ram_used_mb=2048.0,
            ram_total_mb=4096.0,
            disk_used_gb=16.0,
            disk_total_gb=40.0,
        )
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/monitoring/health")
    monitoring_service._check_frontend_health = original_frontend_check
    monitoring_service._collect_host_resources = original_host_resources

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["services"]) == 3
    assert {item["name"] for item in payload["services"]} == {"backend", "database", "frontend"}
    assert payload["host_resources"]["cpu_percent"] == 25.0


@pytest.mark.asyncio
async def test_monitoring_uptime_empty_series():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_db_result(all_value=[]))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/monitoring/uptime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["window_hours"] == 24
    assert payload["summary"] == []
    assert payload["series"] == []


@pytest.mark.asyncio
async def test_list_error_logs_with_filters_and_pagination():
    item = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        request_id="req-1",
        endpoint="/api/v1/bookings",
        method="POST",
        status_code=500,
        error_code="server_error",
        message="boom",
        created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _db_result(scalar_value=1),  # total
            _db_result(all_value=[item]),  # list
        ]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/logs/errors?page=1&page_size=100&q=boom")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["error_code"] == "server_error"


@pytest.mark.asyncio
async def test_error_log_detail_not_found_404():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_db_result(scalar_or_none=None))

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get(f"/api/v1/superadmin/logs/errors/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"error": "error_log_not_found"}


@pytest.mark.asyncio
async def test_list_activity_logs_timeline_desc():
    newer = SimpleNamespace(
        id=uuid.uuid4(),
        super_admin_id=uuid.uuid4(),
        action_type="tenant_updated",
        entity_type="tenant",
        entity_id=str(uuid.uuid4()),
        tenant_id=uuid.uuid4(),
        metadata_json={"k": "v"},
        created_at=datetime.now(timezone.utc),
    )
    older = SimpleNamespace(
        id=uuid.uuid4(),
        super_admin_id=uuid.uuid4(),
        action_type="tenant_created",
        entity_type="tenant",
        entity_id=str(uuid.uuid4()),
        tenant_id=uuid.uuid4(),
        metadata_json=None,
        created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _db_result(scalar_value=2),
            _db_result(all_value=[newer, older]),
        ]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/logs/activities?page=1&page_size=100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 2
    assert payload["items"][0]["action_type"] == "tenant_updated"


@pytest.mark.asyncio
async def test_monitoring_error_logs_page_size_over_limit_returns_422():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/logs/errors?page=1&page_size=101")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_monitoring_activity_logs_page_size_over_limit_returns_422():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/logs/activities?page=1&page_size=101")

    assert response.status_code == 422
