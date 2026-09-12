from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models import Notification, User
from app.core.redis import redis_cache
from app.schemas.notification import NotificationResponse
from app.services.realtime_service import queue_realtime_event


def _cache_key(user_id: int, unread_only: bool) -> str:
    return f"notifications:user:{user_id}:unread:{int(unread_only)}"


def invalidate_notification_cache(user_id: int) -> None:
    redis_cache.delete(_cache_key(user_id, False), _cache_key(user_id, True))


def create_notification(
    db: Session,
    *,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    task_id: Optional[int] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        task_id=task_id,
    )
    db.add(notification)
    queue_realtime_event(db, {
        "type": "notification",
        "notification_type": notification_type,
        "user_id": user_id,
        "related_entity_type": related_entity_type,
        "related_entity_id": related_entity_id,
        "task_id": task_id,
        "title": title,
        "message": message,
    })
    invalidate_notification_cache(user_id)
    return notification


def ensure_notification_owner(notification: Notification, user: User) -> None:
    if notification.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this notification.",
        )


class NotificationService:
    @staticmethod
    def list_for_user(user: User, db: Session, unread_only: bool = False):
        cached = redis_cache.get_json(_cache_key(user.id, unread_only))
        if cached is not None:
            return cached
        query = db.query(Notification).filter(Notification.user_id == user.id)
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        notifications = query.order_by(Notification.created_at.desc(), Notification.id.desc()).all()
        payload = [NotificationResponse.model_validate(item).model_dump(mode="json") for item in notifications]
        redis_cache.set_json(_cache_key(user.id, unread_only), payload)
        return payload

    @staticmethod
    def mark_read(notification_id: int, user: User, db: Session) -> Notification:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
        ensure_notification_owner(notification, user)
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            try:
                queue_realtime_event(db, {
                    "type": "notification.read",
                    "user_id": user.id,
                    "notification_id": notification.id,
                })
                db.commit()
                db.refresh(notification)
            except Exception:
                db.rollback()
                raise
            invalidate_notification_cache(user.id)
        return notification

    @staticmethod
    def mark_all_read(user: User, db: Session) -> int:
        now = datetime.now(timezone.utc)
        try:
            queue_realtime_event(db, {
                "type": "notification.read_all",
                "user_id": user.id,
            })
            count = db.query(Notification).filter(
                Notification.user_id == user.id,
                Notification.is_read.is_(False),
            ).update({Notification.is_read: True, Notification.read_at: now}, synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
        invalidate_notification_cache(user.id)
        return count

    @staticmethod
    def delete(notification_id: int, user: User, db: Session) -> None:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
        ensure_notification_owner(notification, user)
        try:
            queue_realtime_event(db, {
                "type": "notification.deleted",
                "user_id": user.id,
                "notification_id": notification.id,
            })
            db.delete(notification)
            db.commit()
        except Exception:
            db.rollback()
            raise
        invalidate_notification_cache(user.id)
