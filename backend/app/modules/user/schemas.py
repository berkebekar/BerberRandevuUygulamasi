"""user/schemas.py — Müşteri request/response şemaları."""

import uuid

from pydantic import BaseModel, field_validator


class UserMeResponse(BaseModel):
    """Giriş yapmış müşteri bilgisi."""

    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str


class UpdateProfileRequest(BaseModel):
    first_name: str
    last_name: str

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("En az 2 karakter olmalıdır.")
        if len(v) > 100:
            raise ValueError("En fazla 100 karakter olabilir.")
        return v
