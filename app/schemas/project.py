from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.roles import MembershipRole


class ProjectCreate(BaseModel):
    team_id: int
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    team_id: int
    owner_id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberCreate(BaseModel):
    user_id: int
    role: MembershipRole = MembershipRole.MEMBER


class ProjectMemberResponse(BaseModel):
    id: int
    project_id: int
    user_id: int
    role: MembershipRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)