from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.core.roles import UserRole


class UserBase(BaseModel):
    """Base fields shared across User schemas."""
    username: str = Field(..., min_length=3, max_length=50, examples=["swetank"])
    email: EmailStr = Field(..., examples=["swetank@example.com"])


class UserCreate(UserBase):
    """Schema for User Registration request."""
    password: str = Field(..., min_length=8, max_length=72, examples=["StrongPassword123"])


class UserResponse(UserBase):
    """
    Schema for User response.
    IMPORTANT: Never include password_hash in response models!
    """
    id: int
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    """Role changes are accepted only by the admin-protected endpoint."""
    role: UserRole
