from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_member
from app.schemas.activity import ActivityResponse
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.services.comment_service import CommentService


router = APIRouter(tags=["Comments", "Activity"])


@router.post("/tasks/{task_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(task_id: int, data: CommentCreate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return CommentService.create(task_id, data, current_user, db)


@router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
def list_comments(task_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return CommentService.list_for_task(task_id, current_user, db)


@router.get("/tasks/{task_id}/activity", response_model=List[ActivityResponse])
def list_task_activity(task_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return CommentService.activity(task_id, current_user, db)


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
def update_comment(comment_id: int, data: CommentUpdate, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    return CommentService.update(comment_id, data, current_user, db)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, current_user: User = Depends(require_member), db: Session = Depends(get_db)):
    CommentService.delete(comment_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
