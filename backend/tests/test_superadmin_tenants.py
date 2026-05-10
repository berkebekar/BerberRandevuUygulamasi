"""
test_superadmin_tenants.py - Super admin tenant management testleri.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.core.security import create_token_with_secret
from app.main import app
from app.models.activity_log import ActivityLog
from app.models.barber_profile import BarberProfile
from app.models.enums import TenantStatus
from app.modules.superadmin.coolify_service import CoolifyTenantSyncResult, _build_frontend_labels, _merge_domains
from app.modules.superadmin.tenant_schemas import TenantCreateRequest
from app.modules.superadmin.tenant_service import create_tenant, hard_delete_tenant, sync_active_tenant_frontend_domains, update_tenant


def _make_db_result(
    all_value=None,
    scalar_value=None,
    scalar_or_none=None,
    one_value=None,
):
    result = MagicMock()
    result.all.return_value = all_value if all_value is not None else []
    result.scalar_one.return_value = scalar_value
    result.scalar_one_or_none.return_value = scalar_or_none
    result.one.return_value = one_value
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
async def test_tenants_auth_missing_cookie_returns_401():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/tenants")

    assert response.status_code == 401
    assert response.json() == {"error": "not_authenticated"}


@pytest.mark.asyncio
async def test_tenants_auth_wrong_role_returns_403():
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
        response = await client.get("/api/v1/superadmin/tenants")

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_list_tenants_success_with_pagination():
    tenant_1 = SimpleNamespace(
        id=uuid.uuid4(),
        subdomain="acme",
        name="Acme",
        address="Acme Mah. No: 1",
        status=TenantStatus.active,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    tenant_2 = SimpleNamespace(
        id=uuid.uuid4(),
        subdomain="demo",
        name="Demo",
        address="Demo Cad. No: 2",
        status=TenantStatus.inactive,
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )

    total_result = _make_db_result(scalar_value=2)
    tenants_result = _make_db_result()
    tenants_result.scalars.return_value.all.return_value = [tenant_1, tenant_2]
    user_counts_result = _make_db_result(all_value=[(tenant_1.id, 4)])
    booking_counts_result = _make_db_result(all_value=[(tenant_1.id, 10), (tenant_2.id, 1)])

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[total_result, tenants_result, user_counts_result, booking_counts_result]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/tenants?page=1&page_size=50")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 2
    assert payload["pagination"]["page_size"] == 50
    assert len(payload["items"]) == 2
    assert payload["items"][0]["user_count"] == 4
    assert payload["items"][0]["booking_count"] == 10


@pytest.mark.asyncio
async def test_list_tenants_invalid_sort_by_returns_422():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/tenants?sort_by=oops")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_tenant_detail_not_found_404():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=None)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get(f"/api/v1/superadmin/tenants/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"error": "tenant_not_found"}


@pytest.mark.asyncio
async def test_create_tenant_service_transaction_success(monkeypatch):
    super_admin = _override_super_admin()
    body = TenantCreateRequest(
        subdomain="acme-shop",
        name="Acme Shop",
        address="Acme Mah. Randevu Sok. No: 1",
        admin_first_name="Ali",
        admin_last_name="Veli",
        admin_phone="+905551112233",
        admin_email="owner@acme.com",
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(scalar_or_none=None),
            _make_db_result(scalar_or_none=None),
            _make_db_result(scalar_or_none=None),
        ]
    )
    added_objects: list[object] = []

    def _add(obj):
        added_objects.append(obj)

    async def _flush():
        for obj in added_objects:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)

    async def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)

    session.add = MagicMock(side_effect=_add)
    session.flush = AsyncMock(side_effect=_flush)
    session.refresh = AsyncMock(side_effect=_refresh)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    coolify_sync = AsyncMock(
        return_value=CoolifyTenantSyncResult(
            enabled=True,
            domain="https://acme-shop.bbsoft.com.tr",
            domains=["https://acme-shop.bbsoft.com.tr"],
            updated=True,
            deploy_requested=True,
            deployment_uuid="deploy123",
        )
    )
    monkeypatch.setattr("app.modules.superadmin.tenant_service.ensure_tenant_frontend_domain", coolify_sync)

    result = await create_tenant(session, super_admin, body)

    assert result.tenant.subdomain == "acme-shop"
    assert result.tenant.address == "Acme Mah. Randevu Sok. No: 1"
    assert result.admin.email == "owner@acme.com"
    assert result.domain_sync is not None
    assert result.domain_sync.updated is True
    assert result.domain_sync.deploy_requested is True
    assert result.domain_sync.deployment_uuid == "deploy123"
    assert session.commit.await_count == 1
    coolify_sync.assert_awaited_once_with("acme-shop")
    assert any(isinstance(obj, ActivityLog) for obj in added_objects)
    assert any(isinstance(obj, BarberProfile) for obj in added_objects)


def test_coolify_domain_merge_removes_wildcard_and_adds_tenant():
    domains, changed = _merge_domains(
        "https://*.bbsoft.com.tr, https://berber.bbsoft.com.tr",
        "https://cagataycevirgen.bbsoft.com.tr",
    )

    assert changed is True
    assert domains == "https://berber.bbsoft.com.tr,https://cagataycevirgen.bbsoft.com.tr"


def test_coolify_domain_merge_keeps_platform_root_domains():
    domains, changed = _merge_domains(
        "https://berber.bbsoft.com.tr",
        "https://cagataycevirgen.bbsoft.com.tr",
        extra_domains=["https://bbsoft.com.tr", "https://www.bbsoft.com.tr"],
    )

    assert changed is True
    assert domains == (
        "https://berber.bbsoft.com.tr,"
        "https://bbsoft.com.tr,"
        "https://www.bbsoft.com.tr,"
        "https://cagataycevirgen.bbsoft.com.tr"
    )


def test_coolify_frontend_labels_use_explicit_hosts_and_skip_api():
    labels = _build_frontend_labels(
        "frontend123",
        "https://bbsoft.com.tr,https://www.bbsoft.com.tr,https://berber.bbsoft.com.tr,https://api.bbsoft.com.tr,https://demo.bbsoft.com.tr",
        "bbsoft.com.tr",
    )

    assert "Host(`bbsoft.com.tr`)" in labels
    assert "Host(`www.bbsoft.com.tr`)" in labels
    assert "Host(`berber.bbsoft.com.tr`)" in labels
    assert "Host(`demo.bbsoft.com.tr`)" in labels
    assert "Host(`api.bbsoft.com.tr`)" not in labels
    assert "tls.certresolver=letsencrypt" in labels


@pytest.mark.asyncio
async def test_sync_active_tenant_frontend_domains_uses_active_tenants(monkeypatch):
    super_admin = _override_super_admin()
    session = AsyncMock()
    session.add = MagicMock()
    subdomain_result = _make_db_result(all_value=[("berber",), ("berkebekar",)])
    session.execute = AsyncMock(return_value=subdomain_result)
    session.commit = AsyncMock()
    coolify_sync = AsyncMock(
        return_value=CoolifyTenantSyncResult(
            enabled=True,
            domains=[
                "https://bbsoft.com.tr",
                "https://www.bbsoft.com.tr",
                "https://berber.bbsoft.com.tr",
                "https://berkebekar.bbsoft.com.tr",
            ],
            updated=True,
            deploy_requested=True,
            deployment_uuid="deploy456",
            reason="synced",
        )
    )
    monkeypatch.setattr("app.modules.superadmin.tenant_service.sync_tenant_frontend_domains", coolify_sync)

    result = await sync_active_tenant_frontend_domains(session, super_admin)

    coolify_sync.assert_awaited_once_with(["berber", "berkebekar"])
    assert result.tenant_count == 2
    assert result.deploy_requested is True
    assert result.deployment_uuid == "deploy456"
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_create_tenant_service_duplicate_subdomain_409():
    super_admin = _override_super_admin()
    body = TenantCreateRequest(
        subdomain="acme",
        name="Acme Shop",
        address="Acme Mah. No: 1",
        admin_first_name="Ali",
        admin_last_name="Veli",
        admin_phone="+905551112233",
        admin_email="owner@acme.com",
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[_make_db_result(scalar_or_none=uuid.uuid4())]
    )

    with pytest.raises(Exception) as exc_info:
        await create_tenant(session, super_admin, body)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {"error": "subdomain_already_exists"}


@pytest.mark.asyncio
async def test_update_deleted_tenant_returns_409():
    deleted_tenant = SimpleNamespace(
        id=uuid.uuid4(),
        subdomain="old",
        name="Old",
        address="Old Mah. No: 1",
        status=TenantStatus.deleted,
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=deleted_tenant)])

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.put(
            f"/api/v1/superadmin/tenants/{deleted_tenant.id}",
            json={"name": "New Name"},
        )

    assert response.status_code == 409
    assert response.json() == {"error": "tenant_deleted"}


@pytest.mark.asyncio
async def test_update_tenant_commit_integrity_error_maps_to_409():
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        subdomain="acme",
        name="Acme",
        address="Acme Mah. No: 1",
        status=TenantStatus.active,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    admin = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="owner@acme.com",
        phone="+905551112233",
        created_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(scalar_or_none=tenant),
            _make_db_result(scalar_or_none=admin),
            _make_db_result(scalar_or_none=None),
        ]
    )
    session.add = MagicMock()
    session.commit = AsyncMock(
        side_effect=IntegrityError("x", {}, Exception("duplicate key value violates unique constraint admins_email_key"))
    )
    session.rollback = AsyncMock()

    with pytest.raises(Exception) as exc_info:
        await update_tenant(
            session,
            _override_super_admin(),
            tenant.id,
            SimpleNamespace(subdomain=None, name=None, address=None, admin_phone=None, admin_email="OWNER@ACME.COM"),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {"error": "admin_email_already_exists"}


@pytest.mark.asyncio
async def test_status_update_syncs_is_active():
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        status=TenantStatus.active,
        is_active=True,
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=tenant)])
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.put(
            f"/api/v1/superadmin/tenants/{tenant.id}/status",
            json={"status": "inactive", "reason": "maintenance"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "inactive"
    assert payload["is_active"] is False
    assert session.commit.await_count == 1


@pytest.mark.asyncio
async def test_delete_tenant_idempotent_when_already_deleted():
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        status=TenantStatus.deleted,
        is_active=False,
    )
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_make_db_result(scalar_or_none=tenant)])
    session.commit = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.delete(f"/api/v1/superadmin/tenants/{tenant.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_hard_delete_tenant_removes_related_records_and_logs():
    super_admin = _override_super_admin()
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        subdomain="delete-me",
        name="Delete Me",
        status=TenantStatus.deleted,
        is_active=False,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_db_result(scalar_or_none=tenant))
    added_objects: list[object] = []
    session.add = MagicMock(side_effect=added_objects.append)
    session.commit = AsyncMock()

    result = await hard_delete_tenant(session, super_admin, tenant.id)

    assert result.id == tenant.id
    assert result.message == "tenant_hard_deleted"
    assert session.execute.await_count == 13
    assert session.commit.await_count == 1
    assert len(added_objects) == 1
    assert isinstance(added_objects[0], ActivityLog)
    assert added_objects[0].action_type == "tenant_hard_deleted"
    assert added_objects[0].tenant_id is None
