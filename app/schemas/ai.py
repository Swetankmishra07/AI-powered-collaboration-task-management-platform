from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.task import TaskPriority, TaskResponse, TaskStatus


class AITaskCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    project_id: Optional[int] = Field(None, ge=1)
    assignee_id: Optional[int] = Field(None, ge=1)


class AITaskDraft(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.LOW
    deadline: Optional[str] = None
    assignee_id: Optional[int] = None
    project_id: Optional[int] = None


class AITaskCreateResponse(TaskResponse):
    pass


class AISummaryResponse(BaseModel):
    summary: str


class AIPrioritySuggestionResponse(BaseModel):
    priority: TaskPriority
    explanation: str