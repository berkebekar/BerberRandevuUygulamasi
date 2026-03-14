"""
TenantMiddleware tests.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.enums import TenantStatus


def _make_tenant(
    subdomain: str = "berber",
    is_active: bool = True,
    status: TenantStatus | None = TenantStatus.active,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        subdomain=subdomain,
        is_active=is_active,
        status=status,
    )


def _mock_db(tenant: SimpleNamespace | None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = tenant

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)

    mock_sl = MagicMock()
    mock_sl.return_value = context
    return mock_sl


@pytest.mark.asyncio
async def test_unknown_subdomain_returns_404():
    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(None)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test-tenant.localhost",
        ) as client:
            response = await client.get("/api/v1/ping")

    assert response.status_code == 404
    assert response.json() == {"error": "tenant_not_found"}


@pytest.mark.asyncio
async def test_inactive_tenant_status_returns_403():
    tenant = _make_tenant(status=TenantStatus.inactive, is_active=False)

    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(tenant)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://berber.localhost",
        ) as client:
            response = await client.get("/api/v1/ping")

    assert response.status_code == 403
    assert response.json() == {"error": "tenant_inactive"}


@pytest.mark.asyncio
async def test_deleted_tenant_status_returns_404():
    tenant = _make_tenant(status=TenantStatus.deleted, is_active=False)

    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(tenant)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://berber.localhost",
        ) as client:
            response = await client.get("/api/v1/ping")

    assert response.status_code == 404
    assert response.json() == {"error": "tenant_deleted"}


@pytest.mark.asyncio
async def test_legacy_fallback_without_status_uses_is_active():
    tenant = _make_tenant(status=None, is_active=False)

    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(tenant)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://berber.localhost",
        ) as client:
            response = await client.get("/api/v1/ping")

    assert response.status_code == 403
    assert response.json() == {"error": "tenant_inactive"}


@pytest.mark.asyncio
async def test_active_tenant_sets_request_state():
    tenant = _make_tenant(status=TenantStatus.active, is_active=True)

    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(tenant)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://berber.localhost",
        ) as client:
            response = await client.get("/api/v1/ping")

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant.id)
