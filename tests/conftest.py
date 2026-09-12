import os

os.environ["PROJECT_NAME"] = "Smart Task Management API Tests"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-only-secret-key-with-at-least-32-bytes"
os.environ["ENVIRONMENT"] = "testing"
os.environ["REDIS_URL"] = ""

import pytest
from fastapi.testclient import TestClient

from app.database.database import Base, engine
from app.database import models  # noqa: F401
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    """Give each test a clean in-memory schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client