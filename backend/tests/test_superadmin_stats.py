"""
test_superadmin_stats.py - Super admin dashboard stats endpoint testleri.
"""

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_super_admin
from app.core.security import create_token_with_secret
from app.main import app
from app.models.enums import TenantStatus

TZ = ZoneInfo("Europe/Istanbul")


def _make_db_result(
    all_value=None,
    scalar_value=None,
    one_value=None,
    scalars_all_value=None,
) -> MagicMock:
    result = MagicMock()
    result.all.return_value = all_value if all_value is not None else []
    result.scalar_one.return_value = scalar_value
    result.one.return_value = one_value
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_all_value if scalars_all_value is not None else []
    result.scalars.return_value = scalars_obj
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
async def test_overview_success_with_zero_total_cancel_rate():
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(
                all_value=[
                    (TenantStatus.active, 3),
                    (TenantStatus.inactive, 1),
                    (TenantStatus.deleted, 1),
                ]
            ),
            _make_db_result(scalar_value=42),
            _make_db_result(
                one_value=SimpleNamespace(total_bookings=0, cancelled_bookings=0),
            ),
        ]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/stats/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenants"] == {"total": 5, "active": 3, "inactive": 1, "deleted": 1}
    assert payload["users"] == {"total": 42}
    assert payload["bookings"] == {"this_month_total": 0}
    assert payload["cancel"] == {"this_month_cancelled": 0, "this_month_cancel_rate": 0.0}


@pytest.mark.asyncio
async def test_trends_returns_last_6_months_with_zero_fill():
    now = datetime.now(TZ)
    current_month_bucket = datetime(now.year, now.month, 1)
    current_month_key = f"{now.year:04d}-{now.month:02d}"

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(all_value=[(current_month_bucket, 12)]),
            _make_db_result(all_value=[(current_month_bucket, 2)]),
            _make_db_result(all_value=[(current_month_bucket, 7)]),
        ]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/stats/trends")

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["bookings_per_month"]) == 6
    assert len(payload["new_tenants_per_month"]) == 6
    assert len(payload["new_users_per_month"]) == 6

    booking_current = next(i for i in payload["bookings_per_month"] if i["month"] == current_month_key)
    tenant_current = next(i for i in payload["new_tenants_per_month"] if i["month"] == current_month_key)
    user_current = next(i for i in payload["new_users_per_month"] if i["month"] == current_month_key)
    assert booking_current["count"] == 12
    assert tenant_current["count"] == 2
    assert user_current["count"] == 7


@pytest.mark.asyncio
async def test_recent_activities_merges_and_limits():
    now = datetime.now(timezone.utc)
    activity_older = SimpleNamespace(
        action_type="tenant_created",
        entity_type="tenant",
        entity_id="t-1",
        tenant_id=uuid.uuid4(),
        super_admin_id=uuid.uuid4(),
        created_at=now,
        metadata_json={"k": "v"},
    )
    activity_newer = SimpleNamespace(
        action_type="tenant_updated",
        entity_type="tenant",
        entity_id="t-2",
        tenant_id=uuid.uuid4(),
        super_admin_id=uuid.uuid4(),
        created_at=now + timedelta(seconds=1),
        metadata_json=None,
    )
    error_newest = SimpleNamespace(
        method="POST",
        endpoint="/api/v1/bookings",
        status_code=500,
        message="server_error",
        tenant_id=uuid.uuid4(),
        error_code="server_error",
        request_id="r-1",
        created_at=now + timedelta(seconds=2),
    )

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_db_result(scalars_all_value=[activity_older, activity_newer]),
            _make_db_result(scalars_all_value=[error_newest]),
        ]
    )

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_super_admin] = _override_super_admin

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/stats/recent-activities?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["source"] == "error_log"
    assert payload["items"][1]["source"] in {"activity_log", "error_log"}


@pytest.mark.asyncio
async def test_stats_auth_missing_cookie_returns_401():
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        response = await client.get("/api/v1/superadmin/stats/overview")

    assert response.status_code == 401
    assert response.json() == {"error": "not_authenticated"}


@pytest.mark.asyncio
async def test_stats_auth_wrong_role_returns_403():
    settings = get_settings()
    secret = settings.super_admin_session_secret or settings.secret_key
    wrong_role_token = create_token_with_secret(
        {"sub": str(uuid.uuid4()), "role": "admin", "sv": str(uuid.uuid4())},
        expires_minutes=30,
        secret_key=secret,
    )
    session = AsyncMock()

    async def override_db():
        yield session

    app.dependency_overrides[get_db] = override_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        client.cookies.set(settings.super_admin_cookie_name, wrong_role_token)
        response = await client.get("/api/v1/superadmin/stats/overview")

    assert response.status_code == 403
    assert response.json() == {"error": "forbidden"}
