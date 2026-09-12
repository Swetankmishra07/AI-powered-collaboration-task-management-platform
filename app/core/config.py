from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings powered by Pydantic BaseSettings.
    Automatically reads environment variables from OS or .env file.
    """
    PROJECT_NAME: str
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "smart-task-management-api"
    JWT_AUDIENCE: str = "smart-task-management-api-client"
    BCRYPT_ROUNDS: int = 12
    REDIS_URL: Optional[str] = None
    REDIS_CACHE_TTL_SECONDS: int = 30
    BACKGROUND_JOBS_ENABLED: bool = False
    BACKGROUND_JOBS_POLL_INTERVAL_SECONDS: float = 5.0
    BACKGROUND_JOBS_MAX_ATTEMPTS: int = 3
    BACKGROUND_JOBS_RETRY_DELAY_SECONDS: int = 30
    BACKGROUND_JOBS_SHUTDOWN_TIMEOUT_SECONDS: float = 10.0
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "openai_compatible"
    AI_API_KEY: Optional[str] = None
    AI_API_URL: Optional[str] = None
    AI_MODEL: Optional[str] = None
    AI_REQUEST_TIMEOUT_SECONDS: float = 20.0
    ATTACHMENT_STORAGE_PROVIDER: str = "local"
    ATTACHMENT_STORAGE_ROOT: str = "./storage/attachments"
    ATTACHMENT_MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024
    CORS_ALLOWED_ORIGINS: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Reject missing, placeholder, or weak signing keys at startup."""
        if value.startswith("replace-") or len(value) < 32:
            raise ValueError("SECRET_KEY must be a random value of at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_deployment_settings(self):
        if self.ENVIRONMENT not in {"development", "testing", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be development, testing, staging, or production")
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY.startswith("replace-"):
                raise ValueError("SECRET_KEY must be replaced before production startup")
            if self.ATTACHMENT_STORAGE_PROVIDER == "local" and self.BACKGROUND_JOBS_ENABLED:
                raise ValueError("Local attachment storage with background jobs is not supported for multi-instance production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
