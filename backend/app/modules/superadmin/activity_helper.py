"""
superadmin/activity_helper.py - Ortak activity log helper'i.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.super_admin import SuperAdmin


async def append_activity_log(
    db: AsyncSession,
    *,
    super_admin: SuperAdmin,
    action_type: str,
    entity_type: str,
    entity_id: str | None = None,
    tenant_id: uuid.UUID | None = None,
    metadata_json: dict | None = None,
) -> None:
    db.add(
        ActivityLog(
            super_admin_id=super_admin.id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            metadata_json=metadata_json,
        )
    )
