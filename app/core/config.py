"""Application configuration using Pydantic Settings."""

from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    APP_NAME: str = "Team Task Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database – defaults to SQLite; set DATABASE_URL env var for PostgreSQL
    DATABASE_URL: str = "sqlite:///./task_manager.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = True

    @model_validator(mode='after')
    def validate_production_security(self) -> 'Settings':
        import logging
        _logger = logging.getLogger("app.config")
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production-use-a-long-random-string":
            _logger.warning(
                "WARNING: Using default SECRET_KEY in production. "
                "Set the SECRET_KEY environment variable immediately!"
            )
        return self


settings = Settings()
