from typing import List

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.dependencies.authorization import require_member
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(False),
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    return NotificationService.list_for_user(current_user, db, unread_only=unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    return NotificationService.mark_read(notification_id, current_user, db)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    NotificationService.mark_all_read(current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    current_user: User = Depends(require_member),
    db: Session = Depends(get_db),
):
    NotificationService.delete(notification_id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)