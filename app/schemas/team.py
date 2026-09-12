from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.roles import MembershipRole


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMemberCreate(BaseModel):
    user_id: int
    role: MembershipRole = MembershipRole.MEMBER


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    role: MembershipRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)