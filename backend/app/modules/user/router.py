"""user/router.py — Müşteri endpoint'leri."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.modules.user.schemas import UpdateProfileRequest, UserMeResponse

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


@router.patch("/me", response_model=UserMeResponse)
async def update_me(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Giriş yapan müşterinin ad ve soyadını günceller."""
    user.first_name = body.first_name
    user.last_name = body.last_name
    await db.commit()
    await db.refresh(user)
    return UserMeResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
    )
