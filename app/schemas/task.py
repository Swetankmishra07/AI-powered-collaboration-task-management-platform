from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    """Controlled set of allowed task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskBase(BaseModel):
    """Base fields shared across Task schemas."""
    title: str = Field(..., min_length=1, max_length=100, examples=["Learn FastAPI"])
    description: Optional[str] = Field(None, examples=["Complete FastAPI CRUD tutorial"])
    status: TaskStatus = Field(default=TaskStatus.PENDING, examples=["pending"])


class TaskCreate(TaskBase):
    """Schema for Task Creation request."""
    pass


class TaskUpdate(BaseModel):
    """Schema for Task Update request. All fields are optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=100, examples=["Learn Advanced FastAPI"])
    description: Optional[str] = Field(None, examples=["Build production-style API"])
    status: Optional[TaskStatus] = Field(None, examples=["completed"])


class TaskResponse(TaskBase):
    """Schema for Task API Response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
