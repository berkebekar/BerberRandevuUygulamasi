"""tenant/router.py — Tenant endpoint'leri iskeleti."""
from fastapi import APIRouter
router = APIRouter(prefix="/tenant", tags=["tenant"])
