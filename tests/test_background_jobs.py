from datetime import datetime, timedelta, timezone

from app.core.config import Settings, settings
from app.database.database import SessionLocal
from app.database.models import BackgroundJob, Notification, Task, User
from app.services.background_job_service import (
    JOB_DEADLINE_REMINDER,
    BackgroundJobRunner,
    BackgroundJobService,
)


def create_task_with_deadline(deadline):
    db = SessionLocal()
    user = User(
        username="jobuser",
        email="jobuser@example.com",
        password_hash="test-hash",
    )
    db.add(user)
    db.flush()
    task = Task(title="Deadline task", creator_id=user.id, deadline=deadline)
    db.add(task)
    db.flush()
    return db, task.id, user.id


def test_deadline_job_uses_fresh_session_and_creates_one_notification():
    db, task_id, user_id = create_task_with_deadline(datetime.now(timezone.utc) - timedelta(minutes=1))
    task = db.query(Task).filter(Task.id == task_id).one()
    BackgroundJobService.enqueue_deadline_reminder(db, task)
    db.commit()
    db.close()

    assert BackgroundJobService.process_once() is True

    check_db = SessionLocal()
    try:
        job = check_db.query(BackgroundJob).filter(BackgroundJob.kind == JOB_DEADLINE_REMINDER).one()
        notifications = check_db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == "task_deadline_reminder",
        ).all()
        assert job.status == "completed"
        assert len(notifications) == 1
        assert notifications[0].task_id == task_id
    finally:
        check_db.close()


def test_enqueue_is_transactional_and_idempotent():
    db = SessionLocal()
    job = BackgroundJobService.enqueue(
        db,
        kind=JOB_DEADLINE_REMINDER,
        payload={"task_id": 999, "deadline": "2026-09-12T00:00:00+00:00"},
        idempotency_key="test-idempotency-key",
    )
    db.rollback()
    assert db.query(BackgroundJob).count() == 0

    duplicate = BackgroundJobService.enqueue(
        db,
        kind=JOB_DEADLINE_REMINDER,
        payload={"task_id": 999, "deadline": "2026-09-12T00:00:00+00:00"},
        idempotency_key="test-idempotency-key",
    )
    assert duplicate.id is None
    db.commit()
    same = BackgroundJobService.enqueue(
        db,
        kind=JOB_DEADLINE_REMINDER,
        payload={"task_id": 999, "deadline": "2026-09-12T00:00:00+00:00"},
        idempotency_key="test-idempotency-key",
    )
    assert same.id == duplicate.id
    db.close()


def test_failed_job_is_recorded_without_raising(monkeypatch):
    monkeypatch.setattr(settings, "BACKGROUND_JOBS_MAX_ATTEMPTS", 1)
    db = SessionLocal()
    BackgroundJobService.enqueue(
        db,
        kind="unknown.kind",
        payload={},
        idempotency_key="failing-job",
    )
    db.commit()
    db.close()

    assert BackgroundJobService.process_once() is True

    check_db = SessionLocal()
    try:
        job = check_db.query(BackgroundJob).filter(BackgroundJob.idempotency_key == "failing-job").one()
        assert job.status == "failed"
        assert job.attempts == 1
        assert "Unknown background job kind" in job.last_error
    finally:
        check_db.close()


def test_background_job_defaults_are_disabled():
    test_settings = Settings(
        PROJECT_NAME="test",
        DATABASE_URL="sqlite://",
        SECRET_KEY="test-only-secret-key-with-at-least-32-bytes",
    )
    assert test_settings.BACKGROUND_JOBS_ENABLED is False
    assert test_settings.BACKGROUND_JOBS_POLL_INTERVAL_SECONDS > 0


def test_runner_can_start_and_stop():
    class IdleProcessor:
        @staticmethod
        def process_once():
            return False

    runner = BackgroundJobRunner(IdleProcessor)
    runner.start()
    assert runner.is_running
    runner.stop()
    assert not runner.is_running