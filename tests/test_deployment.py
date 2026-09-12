import pytest

from app.core.config import Settings


def test_production_rejects_local_storage_with_enabled_in_process_worker():
    with pytest.raises(ValueError, match="Local attachment storage"):
        Settings(
            PROJECT_NAME="deployment-test",
            DATABASE_URL="postgresql+psycopg://user:password@localhost/db",
            SECRET_KEY="deployment-test-secret-key-with-at-least-32-bytes",
            ENVIRONMENT="production",
            BACKGROUND_JOBS_ENABLED=True,
            ATTACHMENT_STORAGE_PROVIDER="local",
        )


def test_production_accepts_explicit_single_process_configuration():
    settings = Settings(
        PROJECT_NAME="deployment-test",
        DATABASE_URL="postgresql+psycopg://user:password@localhost/db",
        SECRET_KEY="deployment-test-secret-key-with-at-least-32-bytes",
        ENVIRONMENT="production",
        BACKGROUND_JOBS_ENABLED=False,
    )

    assert settings.ENVIRONMENT == "production"