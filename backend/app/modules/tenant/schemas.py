"""tenant/schemas.py - Legacy tenant module placeholder.

Intentional stub. Schemas live in modules/superadmin/tenant_schemas.py.
"""

from pydantic import BaseModel


class TenantLegacyPlaceholder(BaseModel):
    """Keeps module import-safe until legacy module is removed."""

    message: str = "legacy_tenant_module_stub"
