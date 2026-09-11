from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.auth import get_current_user
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GET /tasks Endpoint
    """
    return TaskService.get_user_tasks(current_user, db)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task by ID",
    description="Fetches a specific task by ID if owned by the authenticated user."
)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    DELETE /tasks/{task_id} Endpoint
    """
    TaskService.delete_task(task_id, current_user, db)
    return None
