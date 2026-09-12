from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import ActivityLog, Comment, User
from app.dependencies.authorization import require_member
from app.schemas.ai import (
    AIPrioritySuggestionResponse,
    AISummaryResponse,
    AITaskCreateRequest,
    AITaskCreateResponse,
)
from app.schemas.task import TaskCreate
from app.services.ai_service import AIConfigurationError, AIProviderError, AIService
from app.services.task_service import TaskService


router = APIRouter(prefix="/ai", tags=["AI"])
ai_service = AIService()


def _ai_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AIConfigurationError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI features are not configured.")
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="AI provider is unavailable or returned invalid data.")


def _task_context(task, db: Session) -> dict[str, Any]:
    comments = db.query(Comment).filter(Comment.task_id == task.id).order_by(Comment.id).all()
    activity = db.query(ActivityLog).filter(ActivityLog.task_id == task.id).order_by(ActivityLog.id).all()
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "deadline": task.deadline.isoformat() if isinstance(task.deadline, datetime) else task.deadline,
        },
        "comments": [{"body": comment.body, "created_at": comment.created_at.isoformat()} for comment in comments],
        "activity": [
            {"action": event.action, "entity_type": event.entity_type, "metadata": event.metadata_json}
            for event in activity
        ],
    }


@router.post("/tasks/from-text", response_model=AITaskCreateResponse, status_code=status.HTTP_201_CREATED)
def create_task_from_text(
    request: AITaskCreateRequest,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    try:
        draft = ai_service.create_task(request.prompt)
        task_data = TaskCreate(
            title=draft.title,
            description=draft.description,
            status=draft.status,
            priority=draft.priority,
            deadline=draft.deadline,
            assignee_id=request.assignee_id if request.assignee_id is not None else draft.assignee_id,
            project_id=request.project_id if request.project_id is not None else draft.project_id,
        )
        return TaskService.create_task(task_data, current_user, db)
    except (AIConfigurationError, AIProviderError) as exc:
        raise _ai_error(exc) from exc


@router.post("/tasks/{task_id}/summary", response_model=AISummaryResponse)
def summarize_task(
    task_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    task = TaskService.get_task_by_id(task_id, current_user, db)
    try:
        return {"summary": ai_service.summarize_task(_task_context(task, db))}
    except (AIConfigurationError, AIProviderError) as exc:
        raise _ai_error(exc) from exc


@router.post("/tasks/{task_id}/priority-suggestion", response_model=AIPrioritySuggestionResponse)
def suggest_task_priority(
    task_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    task = TaskService.get_task_by_id(task_id, current_user, db)
    try:
        priority, explanation = ai_service.suggest_priority(_task_context(task, db))
        return {"priority": priority, "explanation": explanation}
    except (AIConfigurationError, AIProviderError) as exc:
        raise _ai_error(exc) from exc