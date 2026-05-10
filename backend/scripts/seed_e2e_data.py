"""
seed_e2e_data.py - ADIM 14 Playwright senaryolari icin deterministik veri hazirlar.
"""

import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.admin import Admin
from app.models.enums import TenantStatus, UserStatus
from app.models.super_admin import SuperAdmin
from app.models.tenant import Tenant
from app.models.user import User


async def _ensure_super_admin(db) -> tuple[str, str]:
    username = os.getenv("E2E_SUPERADMIN_USERNAME", "e2e_owner")
    password = os.getenv("E2E_SUPERADMIN_PASSWORD", "E2E_owner_123!")

    result = await db.execute(select(SuperAdmin).where(SuperAdmin.username == username))
    super_admin = result.scalar_one_or_none()
    if super_admin is None:
        super_admin = SuperAdmin(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
            session_version=str(uuid.uuid4()),
        )
        db.add(super_admin)
    else:
        super_admin.password_hash = hash_password(password)
        super_admin.is_active = True
        super_admin.session_version = str(uuid.uuid4())
    return username, password


async def _ensure_tenant_and_admin(db) -> tuple[Tenant, Admin]:
    subdomain = os.getenv("E2E_TENANT_SUBDOMAIN", "e2e-tenant")
    tenant_name = os.getenv("E2E_TENANT_NAME", "E2E Tenant")
    tenant_address = os.getenv("E2E_TENANT_ADDRESS", "E2E Mah. Test Sok. No: 1")

    tenant_result = await db.execute(select(Tenant).where(Tenant.subdomain == subdomain))
    tenant = tenant_result.scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(
            subdomain=subdomain,
            name=tenant_name,
            address=tenant_address,
            status=TenantStatus.active,
            is_active=True,
        )
        db.add(tenant)
        await db.flush()
    else:
        tenant.name = tenant_name
        tenant.address = tenant_address
        tenant.status = TenantStatus.active
        tenant.is_active = True

    admin_email = os.getenv("E2E_ADMIN_EMAIL", "e2e.admin@example.com")
    admin_phone = os.getenv("E2E_ADMIN_PHONE", "+905551110000")

    admin_result = await db.execute(select(Admin).where(Admin.tenant_id == tenant.id))
    admin = admin_result.scalar_one_or_none()
    if admin is None:
        admin = Admin(
            tenant_id=tenant.id,
            email=admin_email,
            phone=admin_phone,
            session_version=str(uuid.uuid4()),
        )
        db.add(admin)
    else:
        admin.email = admin_email
        admin.phone = admin_phone
        admin.session_version = str(uuid.uuid4())

    return tenant, admin


async def _ensure_user(db, tenant_id) -> User:
    phone = os.getenv("E2E_USER_PHONE", "+905551110001")
    first_name = os.getenv("E2E_USER_FIRST_NAME", "E2E")
    last_name = os.getenv("E2E_USER_LAST_NAME", "User")

    user_result = await db.execute(select(User).where(User.tenant_id == tenant_id, User.phone == phone))
    user = user_result.scalar_one_or_none()
    if user is None:
        user = User(
            tenant_id=tenant_id,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            status=UserStatus.active,
            is_blocked=False,
            session_version=str(uuid.uuid4()),
        )
        db.add(user)
    else:
        user.first_name = first_name
        user.last_name = last_name
        user.status = UserStatus.active
        user.is_blocked = False
        user.session_version = str(uuid.uuid4())

    return user


async def main():
    async with AsyncSessionLocal() as db:
        username, password = await _ensure_super_admin(db)
        tenant, _admin = await _ensure_tenant_and_admin(db)
        user = await _ensure_user(db, tenant.id)
        await db.commit()

        payload = {
            "superadmin_username": username,
            "superadmin_password": password,
            "seeded_tenant_id": str(tenant.id),
            "seeded_tenant_subdomain": tenant.subdomain,
            "seeded_user_id": str(user.id),
            "seeded_user_phone": user.phone,
        }
        print(json.dumps(payload))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
