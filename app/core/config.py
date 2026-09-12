from typing import Optional

from pydantic import field_validator
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

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Reject missing, placeholder, or weak signing keys at startup."""
        if value.startswith("replace-") or len(value) < 32:
            raise ValueError("SECRET_KEY must be a random value of at least 32 characters")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
