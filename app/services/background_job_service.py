import logging
import threading
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.database import SessionLocal
from app.database.models import BackgroundJob, Notification, Task
from app.services.notification_service import create_notification


logger = logging.getLogger(__name__)

JOB_NOTIFICATION = "notification.process"
JOB_DEADLINE_REMINDER = "deadline.reminder"
JOB_REPORT = "report.process"
JOB_AI = "ai.process"

JobHandler = Callable[[Session, dict[str, Any]], None]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _notification_exists(db: Session, payload: dict[str, Any]) -> bool:
    query = db.query(Notification).filter(
        Notification.user_id == payload["user_id"],
        Notification.type == payload["notification_type"],
    )
    if payload.get("task_id") is not None:
        query = query.filter(Notification.task_id == payload["task_id"])
    if payload.get("related_entity_id") is not None:
        query = query.filter(Notification.related_entity_id == payload["related_entity_id"])
    return query.first() is not None


def process_notification_job(db: Session, payload: dict[str, Any]) -> None:
    """Create a notification once; retries cannot create another copy."""
    if _notification_exists(db, payload):
        return
    create_notification(
        db,
        user_id=payload["user_id"],
        notification_type=payload["notification_type"],
        title=payload["title"],
        message=payload["message"],
        related_entity_type=payload.get("related_entity_type"),
        related_entity_id=payload.get("related_entity_id"),
        task_id=payload.get("task_id"),
    )


def process_deadline_reminder_job(db: Session, payload: dict[str, Any]) -> None:
    task = db.query(Task).filter(Task.id == payload["task_id"]).first()
    if task is None or task.deadline is None or task.status == "completed":
        return
    if _as_utc(task.deadline).isoformat() != payload["deadline"]:
        return

    recipient_id = task.assignee_id or task.creator_id
    process_notification_job(db, {
        "user_id": recipient_id,
        "notification_type": "task_deadline_reminder",
        "title": "Task deadline reached",
        "message": f"The deadline for task '{task.title}' has been reached.",
        "related_entity_type": "task",
        "related_entity_id": task.id,
        "task_id": task.id,
    })


def _future_hook(_: Session, __: dict[str, Any]) -> None:
    raise NotImplementedError("This background job hook is reserved for a future phase.")


JOB_HANDLERS: dict[str, JobHandler] = {
    JOB_NOTIFICATION: process_notification_job,
    JOB_DEADLINE_REMINDER: process_deadline_reminder_job,
    JOB_REPORT: _future_hook,
    JOB_AI: _future_hook,
}


class BackgroundJobService:
    """Enqueue and process durable jobs without sharing request sessions."""

    @staticmethod
    def enqueue(
        db: Session,
        *,
        kind: str,
        payload: dict[str, Any],
        idempotency_key: str,
        available_at: Optional[datetime] = None,
    ) -> BackgroundJob:
        existing = db.query(BackgroundJob).filter(
            BackgroundJob.idempotency_key == idempotency_key,
        ).first()
        if existing is not None:
            return existing
        job = BackgroundJob(
            kind=kind,
            payload=payload,
            idempotency_key=idempotency_key,
            available_at=available_at or _utc_now(),
        )
        db.add(job)
        return job

    @staticmethod
    def enqueue_deadline_reminder(db: Session, task: Task) -> Optional[BackgroundJob]:
        if task.deadline is None:
            return None
        deadline = _as_utc(task.deadline).isoformat()
        return BackgroundJobService.enqueue(
            db,
            kind=JOB_DEADLINE_REMINDER,
            payload={"task_id": task.id, "deadline": deadline},
            idempotency_key=f"deadline-reminder:{task.id}:{deadline}",
            available_at=task.deadline,
        )

    @staticmethod
    def _claim_next(db: Session) -> Optional[BackgroundJob]:
        now = _utc_now()
        candidate = db.query(BackgroundJob).filter(
            BackgroundJob.status.in_(("pending", "retry")),
            BackgroundJob.available_at <= now,
        ).order_by(BackgroundJob.available_at, BackgroundJob.id).first()
        if candidate is None:
            return None
        claimed = db.query(BackgroundJob).filter(
            BackgroundJob.id == candidate.id,
            BackgroundJob.status.in_(("pending", "retry")),
            BackgroundJob.available_at <= now,
        ).update({
            BackgroundJob.status: "processing",
            BackgroundJob.claimed_at: now,
            BackgroundJob.attempts: BackgroundJob.attempts + 1,
        }, synchronize_session=False)
        if claimed != 1:
            db.rollback()
            return None
        db.commit()
        return db.query(BackgroundJob).filter(BackgroundJob.id == candidate.id).one()

    @staticmethod
    def process_once() -> bool:
        claim_db = SessionLocal()
        try:
            job = BackgroundJobService._claim_next(claim_db)
        except Exception:
            claim_db.rollback()
            logger.exception("Unable to claim a background job")
            return False
        finally:
            claim_db.close()

        if job is None:
            return False

        work_db = SessionLocal()
        failure: Optional[Exception] = None
        try:
            handler = JOB_HANDLERS.get(job.kind)
            if handler is None:
                raise ValueError(f"Unknown background job kind: {job.kind}")
            handler(work_db, job.payload)
            work_db.commit()
        except Exception as exc:
            work_db.rollback()
            logger.exception("Background job %s failed", job.id)
            failure = exc
        finally:
            work_db.close()
        if failure is not None:
            BackgroundJobService._record_failure(job.id, str(failure), job.attempts)
        else:
            BackgroundJobService._record_success(job.id)
        return True

    @staticmethod
    def _record_success(job_id: int) -> None:
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job is not None:
                job.status = "completed"
                job.completed_at = _utc_now()
                job.last_error = None
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to mark background job %s complete", job_id)
        finally:
            db.close()

    @staticmethod
    def _record_failure(job_id: int, error: str, attempts: int) -> None:
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job is not None:
                if attempts >= settings.BACKGROUND_JOBS_MAX_ATTEMPTS:
                    job.status = "failed"
                else:
                    job.status = "retry"
                    job.available_at = _utc_now() + timedelta(seconds=settings.BACKGROUND_JOBS_RETRY_DELAY_SECONDS)
                job.last_error = error[:2000]
                db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to record background job %s failure", job_id)
        finally:
            db.close()


class BackgroundJobRunner:
    """Small opt-in polling worker suitable for one API process."""

    def __init__(self, processor: type[BackgroundJobService] = BackgroundJobService) -> None:
        self._processor = processor
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="background-job-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=settings.BACKGROUND_JOBS_SHUTDOWN_TIMEOUT_SECONDS)
            self._thread = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            started = monotonic()
            while self._processor.process_once() and not self._stop_event.is_set():
                pass
            remaining = settings.BACKGROUND_JOBS_POLL_INTERVAL_SECONDS - (monotonic() - started)
            if remaining > 0:
                self._stop_event.wait(remaining)