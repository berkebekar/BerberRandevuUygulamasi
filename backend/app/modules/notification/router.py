"""notification/router.py — Bildirim endpoint'leri iskeleti."""
from fastapi import APIRouter
router = APIRouter(prefix="/notifications", tags=["notifications"])
