from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_member
from app.schemas.task import TaskCreate, TaskPriority, TaskResponse, TaskStatus, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description="Creates a task associated strictly with the authenticated user."
)
def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db)
):
    """
    POST /tasks Endpoint
    """
    return TaskService.create_task(task_data, current_user, db)


@router.get(
    "",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all user tasks",
    description="Returns a list of tasks belonging strictly to the authenticated user."
)
def get_tasks(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    task_status: Optional[TaskStatus] = Query(None, alias="status"),
    priority: Optional[TaskPriority] = None,
    assignee_id: Optional[int] = Query(None, ge=1),
    project_id: Optional[int] = Query(None, ge=1),
    deadline_before: Optional[datetime] = None,
    deadline_after: Optional[datetime] = None,
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    sort_by: Literal["created_at", "updated_at", "deadline", "title", "status", "priority"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db)
):
    """
    GET /tasks Endpoint
    """
    return TaskService.get_user_tasks(
        current_user,
        db,
        limit=limit,
        offset=offset,
        task_status=task_status,
        priority=priority,
        assignee_id=assignee_id,
        project_id=project_id,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task by ID",
    description="Fetches a specific task by ID if owned by the authenticated user."
)
def get_task(
    task_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db)
):
    """
    GET /tasks/{task_id} Endpoint
    """
    return TaskService.get_task_by_id(task_id, current_user, db)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task",
    description="Updates task details if owned by the authenticated user."
)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db)
):
    """
    PUT /tasks/{task_id} Endpoint
    """
    return TaskService.update_task(task_id, task_data, current_user, db)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description="Deletes a task if owned by the authenticated user."
)
def delete_task(
    task_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db)
):
    """
    DELETE /tasks/{task_id} Endpoint
    """
    TaskService.delete_task(task_id, current_user, db)
    return None
