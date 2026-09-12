from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database.models import ActivityLog, User


def record_activity(
    db: Session,
    *,
    actor: Optional[User],
    action: str,
    entity_type: str,
    entity_id: int,
    task_id: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
    notifications: Optional[list[dict[str, Any]]] = None,
) -> ActivityLog:
    """Append an audit event to the current transaction."""
    event = ActivityLog(
        actor_id=actor.id if actor else None,
        task_id=task_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )
    db.add(event)
    if notifications:
        from app.services.notification_service import create_notification

        for notification in notifications:
            create_notification(db, **notification)
    return event
