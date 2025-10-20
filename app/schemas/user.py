"""Pydantic schemas for authentication and users."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    """Common subset of user fields."""

    email: EmailStr


class UserCreate(UserBase):
    """Payload for creating a user."""

    password: str = Field(min_length=8, max_length=72)
    ong: str = Field(min_length=1, max_length=128)
    nombre: str = Field(min_length=1, max_length=128)
    apellido: str = Field(min_length=1, max_length=128)
    role: Optional[UserRole] = Field(default=None)


class UserLogin(UserBase):
    """Login payload."""

    password: str = Field(min_length=1, max_length=128)


class UserResponse(UserBase):
    """User data returned by the API."""

    id: UUID
    ong: str
    nombre: str
    apellido: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    """Bearer token pair."""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenRefreshRequest(BaseModel):
    """Refresh token request payload."""

    refresh_token: str = Field(min_length=1)
