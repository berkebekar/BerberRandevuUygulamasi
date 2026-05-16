"""Tenant based WhatsApp send settings."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.tenant import Tenant


@dataclass(frozen=True)
class TenantWhatsappCredentials:
    phone_number_id: str
    access_token: str


async def get_tenant_whatsapp_credentials(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> TenantWhatsappCredentials | None:
    settings = get_settings()
    if not settings.wa_access_token:
        return None

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return None

    phone_number_id = (getattr(tenant, "whatsapp_phone_number_id", None) or "").strip()
    status = getattr(tenant, "whatsapp_connection_status", "disconnected")
    if not phone_number_id or status != "connected":
        return None

    return TenantWhatsappCredentials(
        phone_number_id=phone_number_id,
        access_token=settings.wa_access_token,
    )
