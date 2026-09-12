from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models import Comment, User
from app.schemas.comment import CommentCreate, CommentUpdate
from app.services.activity_service import record_activity
from app.services.task_service import TaskService
from app.services.realtime_service import queue_realtime_event


def _get_comment(comment_id: int, db: Session) -> Comment:
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")
    return comment


def _ensure_comment_access(comment: Comment, user: User, db: Session) -> None:
    TaskService.get_task_by_id(comment.task_id, user, db)


class CommentService:
    @staticmethod
    def create(task_id: int, data: CommentCreate, user: User, db: Session) -> Comment:
        task = TaskService.get_task_by_id(task_id, user, db)
        comment = Comment(task_id=task.id, author_id=user.id, body=data.body)
        recipient_ids = {task.creator_id, task.assignee_id} - {user.id, None}
        try:
            db.add(comment)
            db.flush()
            record_activity(
                db,
                actor=user,
                action="comment_created",
                entity_type="comment",
                entity_id=comment.id,
                task_id=task.id,
                notifications=[{
                    "user_id": recipient_id,
                    "notification_type": "comment_added",
                    "title": "New task comment",
                    "message": f"A new comment was added to task '{task.title}'.",
                    "related_entity_type": "comment",
                    "related_entity_id": comment.id,
                    "task_id": task.id,
                } for recipient_id in recipient_ids],
            )
            queue_realtime_event(db, {
                "type": "comment.created",
                "task_id": task.id,
                "comment_id": comment.id,
                "actor_id": user.id,
                "body": comment.body,
            })
            db.commit()
            db.refresh(comment)
        except Exception:
            db.rollback()
            raise
        return comment

    @staticmethod
    def list_for_task(task_id: int, user: User, db: Session) -> List[Comment]:
        TaskService.get_task_by_id(task_id, user, db)
        return db.query(Comment).filter(Comment.task_id == task_id).order_by(Comment.id.asc()).all()

    @staticmethod
    def update(comment_id: int, data: CommentUpdate, user: User, db: Session) -> Comment:
        comment = _get_comment(comment_id, db)
        _ensure_comment_access(comment, user, db)
        if comment.author_id != user.id and user.role not in {"admin", "manager"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit this comment.")
        comment.body = data.body
        try:
            db.flush()
            record_activity(
                db,
                actor=user,
                action="comment_updated",
                entity_type="comment",
                entity_id=comment.id,
                task_id=comment.task_id,
            )
            queue_realtime_event(db, {
                "type": "comment.updated",
                "task_id": comment.task_id,
                "comment_id": comment.id,
                "actor_id": user.id,
                "body": comment.body,
            })
            db.commit()
            db.refresh(comment)
        except Exception:
            db.rollback()
            raise
        return comment

    @staticmethod
    def delete(comment_id: int, user: User, db: Session) -> None:
        comment = _get_comment(comment_id, db)
        _ensure_comment_access(comment, user, db)
        if comment.author_id != user.id and user.role not in {"admin", "manager"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete this comment.")
        try:
            record_activity(
                db,
                actor=user,
                action="comment_deleted",
                entity_type="comment",
                entity_id=comment.id,
                task_id=comment.task_id,
            )
            queue_realtime_event(db, {
                "type": "comment.deleted",
                "task_id": comment.task_id,
                "comment_id": comment.id,
                "actor_id": user.id,
            })
            db.delete(comment)
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def activity(task_id: int, user: User, db: Session) -> List:
        TaskService.get_task_by_id(task_id, user, db)
        from app.database.models import ActivityLog

        return db.query(ActivityLog).filter(
            ActivityLog.task_id == task_id
        ).order_by(ActivityLog.created_at.asc(), ActivityLog.id.asc()).all()
