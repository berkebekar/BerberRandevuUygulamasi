"""
Super admin auth schema'lari.
"""

from pydantic import BaseModel, Field


class SuperAdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=255)


class SuperAdminLoginResponse(BaseModel):
    message: str
