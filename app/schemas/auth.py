from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Schema for User Login request."""
    email: EmailStr = Field(..., examples=["swetank@example.com"])
    password: str = Field(..., min_length=8, max_length=72, examples=["StrongPassword123"])


class TokenResponse(BaseModel):
    """Schema for an access and rotating refresh-token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing or revoking a session."""
    refresh_token: str = Field(..., min_length=40)


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload data."""
    sub: Optional[str] = None
    user_id: Optional[int] = None
