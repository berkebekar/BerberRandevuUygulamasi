"""user/schemas.py — Müşteri request/response şemaları."""

import uuid

from pydantic import BaseModel


class UserMeResponse(BaseModel):
    """Giriş yapmış müşteri bilgisi."""

    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str
