"""
test_tenant_middleware.py — TenantMiddleware için otomatik testler.

Test senaryoları:
  1. Geçersiz subdomain (DB'de yok) → 404 + {"error": "tenant_not_found"}
  2. is_active=False tenant → 403 + {"error": "tenant_inactive"}
  3. Geçerli tenant → 200 + request.state.tenant_id set edilmiş

Gerçek DB bağlantısı gerekmez; AsyncSessionLocal unittest.mock ile mock'lanır.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _make_tenant(subdomain: str = "berber", is_active: bool = True) -> SimpleNamespace:
    """
    Test için sahte bir tenant nesnesi oluşturur.
    SQLAlchemy mapper'ı atlamak için SimpleNamespace kullanılır —
    middleware sadece .id ve .is_active alanlarına erişir.
    """
    return SimpleNamespace(id=uuid.uuid4(), subdomain=subdomain, is_active=is_active)


def _mock_db(tenant: SimpleNamespace | None):
    """
    AsyncSessionLocal() çağrısını mock'lar.
    tenant=None → DB'de kayıt yok gibi davranır.
    tenant=<Tenant> → o kaydı döndürür.
    """
    # execute() sonucu: scalar_one_or_none() → tenant veya None
    result = MagicMock()
    result.scalar_one_or_none.return_value = tenant

    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)

    # "async with AsyncSessionLocal() as session:" yapısını taklit et
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)

    mock_sl = MagicMock()
    mock_sl.return_value = context
    return mock_sl


@pytest.mark.asyncio
async def test_gecersiz_subdomain_404():
    """
    DB'de bulunmayan bir subdomain ile gelen request 404 almalı.
    "test-tenant" subdomain'i DB'de yok → tenant_not_found.
    """
    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(None)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test-tenant.localhost",
        ) as client:
            r = await client.get("/api/v1/ping")

    assert r.status_code == 404
    assert r.json() == {"error": "tenant_not_found"}


@pytest.mark.asyncio
async def test_inactive_tenant_403():
    """
    is_active=False olan tenant ile gelen request 403 almalı.
    Subdomain DB'de var ama tenant pasif → tenant_inactive.
    """
    inactive = _make_tenant(subdomain="berber", is_active=False)

    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(inactive)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://berber.localhost",
        ) as client:
            r = await client.get("/api/v1/ping")

    assert r.status_code == 403
    assert r.json() == {"error": "tenant_inactive"}


@pytest.mark.asyncio
async def test_gecerli_tenant_state_set():
    """
    Geçerli tenant ile gelen request'te request.state.tenant_id set edilmeli.
    /api/v1/ping endpoint'i tenant_id'yi response'a yazar; doğrulama buradan yapılır.
    """
    tenant = _make_tenant(subdomain="berber", is_active=True)

    with patch("app.middleware.tenant_middleware.AsyncSessionLocal", _mock_db(tenant)):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://berber.localhost",
        ) as client:
            r = await client.get("/api/v1/ping")

    assert r.status_code == 200
    assert r.json()["tenant_id"] == str(tenant.id)
