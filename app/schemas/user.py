import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base shared user attributes."""
    email: EmailStr = Field(..., description="User's valid email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of user")
    role: str = Field(default="CUSTOMER", description="Role: 'CUSTOMER' or 'ADMIN'")


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain password, minimum 8 characters",
    )


class UserLogin(BaseModel):
    """Schema for standard JSON login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for public user profile responses (excludes hashed_password)."""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

