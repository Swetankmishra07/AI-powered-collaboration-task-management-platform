import os
import tempfile
from pathlib import Path

os.environ["PROJECT_NAME"] = "Smart Task Management API Tests"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-bytes"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REDIS_URL"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.database import database
from app.database import models  # noqa: F401
from app.main import app, background_job_runner
from app.services.realtime_service import connection_manager


@pytest.fixture(autouse=True)
def reset_database():
    """Give each test an isolated SQLite database and clean runtime state."""
    previous_engine = database.engine
    database_fd, database_path = tempfile.mkstemp(prefix="smart-task-test-", suffix=".sqlite3")
    os.close(database_fd)
    test_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    database.SessionLocal.configure(bind=test_engine)
    database.engine = test_engine
    database.Base.metadata.create_all(bind=test_engine)
    connection_manager._connections.clear()
    connection_manager._connection_loops.clear()
    try:
        yield
    finally:
        if background_job_runner.is_running:
            background_job_runner.stop()
        connection_manager._connections.clear()
        connection_manager._connection_loops.clear()
        database.Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
        Path(database_path).unlink(missing_ok=True)
        database.SessionLocal.configure(bind=previous_engine)
        database.engine = previous_engine


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client