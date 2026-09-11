import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings powered by Pydantic BaseSettings.
    Automatically reads environment variables from OS or .env file.
    """
    PROJECT_NAME: str = "Smart Task Management API"
    VERSION: str = "1.0.0"
    
    # Database URL
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/task_db"
    
    # JWT Security Settings
    SECRET_KEY: str = "super-secret-key-change-this-in-production-123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
