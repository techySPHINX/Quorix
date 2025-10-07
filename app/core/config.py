import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, EmailStr, HttpUrl, ValidationInfo, field_validator
from pydantic_settings import BaseSettings

# Import the new advanced settings
from app.core.settings import get_settings as get_advanced_settings


class Settings(BaseSettings):
    # API & Security
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30

    # Server
    # Provide safe defaults for CI/test environments. These can be overridden
    # via environment variables or a .env file in production deployments.
    SERVER_NAME: str = "quorix"
    SERVER_HOST: str = "http://localhost:8000"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")  # type: ignore[misc]
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]], info: ValidationInfo
    ) -> Union[str, List[str]]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [v]
        raise ValueError(f"Invalid CORS origins: {v}")

    # Project
    PROJECT_NAME: str = "Quorix"
    SENTRY_DSN: Optional[HttpUrl] = None

    # Database & Redis
    # Use in-memory async SQLite for tests by default and local redis fallback URL.
    # When using SQLite with SQLAlchemy's asyncio engine, use the aiosqlite driver.
    SQLALCHEMY_DATABASE_URI: str = "sqlite+aiosqlite:///:memory:"
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # Celery
    # Default to a simple in-memory backend alternative for tests. CI or
    # production should set real broker/backends via env vars.
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_ROUTES: Dict[str, Dict[str, str]] = {
        "app.tasks.send_*": {"queue": "email"},
        "app.tasks.notify_*": {"queue": "notifications"},
    }

    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: Optional[EmailStr] = None
    SENDGRID_FROM_NAME: Optional[str] = None

    @field_validator("SENDGRID_FROM_NAME", mode="before")  # type: ignore[misc]
    @classmethod
    def get_sendgrid_from_name(
        cls, v: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        if v:
            return v
        values: Dict[str, Any] = info.data if info.data else {}
        return str(values.get("PROJECT_NAME", "Evently"))

    # Email Templates
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEMPLATES_DIR: str = "app/templates/email"
    EMAIL_TEMPLATES_ENABLED: bool = True
    EMAILS_ENABLED: bool = False

    @field_validator("EMAILS_ENABLED", mode="before")  # type: ignore[misc]
    @classmethod
    def get_emails_enabled(cls, v: bool, info: ValidationInfo) -> bool:
        values: Dict[str, Any] = info.data if info.data else {}
        return bool(
            values.get("SENDGRID_API_KEY") and values.get("SENDGRID_FROM_EMAIL")
        )

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changeme"
    USERS_OPEN_REGISTRATION: bool = False

    # Notifications
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_RETENTION_DAYS: int = 90
    NOTIFICATION_BATCH_SIZE: int = 100

    # Email Notification System
    EMAIL_NOTIFICATION_RETRIES: int = 3
    EMAIL_BATCH_SIZE: int = 10
    EMAIL_BATCH_DELAY: float = 1.0

    # Push Notifications (future)
    PUSH_NOTIFICATIONS_ENABLED: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENVIRONMENT: str = "production"

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
    }


settings: Settings = Settings()

# Also provide access to advanced settings
advanced_settings = get_advanced_settings()
