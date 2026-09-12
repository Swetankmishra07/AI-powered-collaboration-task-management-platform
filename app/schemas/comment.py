from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    task_id: int
    author_id: int
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
