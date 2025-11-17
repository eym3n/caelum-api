"""User models and schemas for authentication."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(
        ..., min_length=8, description="Password must be at least 8 characters"
    )


class UserUpdate(BaseModel):
    """Schema for updating user information."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """User schema as stored in database."""

    id: str = Field(alias="_id")
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True)


class User(UserBase):
    """User schema for API responses (public-facing)."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    sub: str  # subject (user ID)
    exp: datetime  # expiration
    type: str  # "access" or "refresh"


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token requests."""

    refresh_token: str
