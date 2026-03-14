"""
superadmin/service.py - Super admin auth business logic.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.super_admin import SuperAdmin


async def authenticate_super_admin(
    db: AsyncSession,
    username: str,
    password: str,
) -> SuperAdmin:
    """
    Username + password ile super admin girisi.
    Basarili giriste session_version rotate edilir.
    """
    result = await db.execute(select(SuperAdmin).where(SuperAdmin.username == username))
    super_admin = result.scalar_one_or_none()

    if super_admin is None or not verify_password(password, super_admin.password_hash):
        raise HTTPException(401, {"error": "invalid_credentials"})

    if not super_admin.is_active:
        raise HTTPException(403, {"error": "super_admin_inactive"})

    super_admin.session_version = str(uuid.uuid4())
    await db.commit()
    await db.refresh(super_admin)
    return super_admin


async def rotate_super_admin_session_version_by_id(
    db: AsyncSession,
    super_admin_id: str,
) -> None:
    """
    Logout'ta session_version degistirerek token'i sunucu tarafinda iptal eder.
    """
    try:
        parsed_id = uuid.UUID(str(super_admin_id))
    except (TypeError, ValueError):
        return

    result = await db.execute(select(SuperAdmin).where(SuperAdmin.id == parsed_id))
    super_admin = result.scalar_one_or_none()
    if super_admin is None:
        return

    super_admin.session_version = str(uuid.uuid4())
    await db.commit()
