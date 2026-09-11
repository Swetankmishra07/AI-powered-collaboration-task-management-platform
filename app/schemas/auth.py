from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for User Login request."""
    email: EmailStr = Field(..., examples=["swetank@example.com"])
    password: str = Field(..., examples=["StrongPassword123"])


class TokenResponse(BaseModel):
    """Schema for JWT Access Token response."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload data."""
    sub: Optional[str] = None
    user_id: Optional[int] = None
