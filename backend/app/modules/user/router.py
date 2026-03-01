"""user/router.py — Müşteri endpoint'leri."""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.user.schemas import UserMeResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserMeResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Giriş yapan müşterinin profil bilgisini döndürür."""
    return UserMeResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
    )
