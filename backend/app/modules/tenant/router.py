"""tenant/router.py - Legacy tenant module placeholder.

This module is intentionally not mounted in app.main.
Tenant management is implemented under modules/superadmin.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/tenant", tags=["tenant"])
