"""
Advanced Configuration & Environment Management for Evently
"""

import logging
import secrets
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pydantic import EmailStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings as PydanticBaseSettings

logger = logging.getLogger(__name__)


class DatabaseSettings(PydanticBaseSettings):
    """Database configuration settings"""

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "evently"

    # Connection Pool Settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    DB_ECHO: bool = False

    # Connection Timeouts
    DB_COMMAND_TIMEOUT: int = 60
    DB_STATEMENT_TIMEOUT: str = "60s"
    DB_LOCK_TIMEOUT: str = "30s"
    DB_IDLE_IN_TRANSACTION_TIMEOUT: str = "10min"

    @property
    def database_url(self) -> str:
        """Generate database URL for async connections"""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        """Generate database URL for sync connections"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_prefix = "DB_"
        case_sensitive = True


class RedisSettings(PydanticBaseSettings):
    """Redis configuration settings"""

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_USERNAME: Optional[str] = None

    # Connection Pool Settings
    REDIS_MAX_CONNECTIONS: int = 100
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 5.0
    REDIS_HEALTH_CHECK_INTERVAL: int = 30

    @property
    def redis_url(self) -> str:
        """Generate Redis URL"""
        auth = ""
        if self.REDIS_USERNAME and self.REDIS_PASSWORD:
            auth = f"{self.REDIS_USERNAME}:{self.REDIS_PASSWORD}@"
        elif self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD}@"

        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_prefix = "REDIS_"
        case_sensitive = True


class SecuritySettings(PydanticBaseSettings):
    """Security and authentication settings"""

    SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    # Password Security
    PASSWORD_HASH_ALGORITHM: str = "bcrypt"
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SYMBOLS: bool = False

    # Encryption
    ENCRYPTION_KEY: str = secrets.token_urlsafe(32)

    # Session Security
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"

    class Config:
        env_prefix = "SECURITY_"
        case_sensitive = True


class ScalabilitySettings(PydanticBaseSettings):
    """Performance and scalability settings"""

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour
    RATE_LIMIT_STORAGE: str = "redis"

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_KEY_PREFIX: str = "evently:"
    CACHE_COMPRESSION: bool = True
    CACHE_SERIALIZER: str = "json"

    # Background Tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: List[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True

    # API Performance
    MAX_REQUEST_SIZE: int = 10 * 1024 * 1024  # 10MB
    REQUEST_TIMEOUT: int = 30
    RESPONSE_COMPRESSION: bool = True
    RESPONSE_COMPRESSION_MINIMUM_SIZE: int = 1000

    # Connection Limits
    MAX_CONCURRENT_CONNECTIONS: int = 1000
    KEEPALIVE_TIMEOUT: int = 65

    class Config:
        env_prefix = "SCALABILITY_"
        case_sensitive = True


class MonitoringSettings(PydanticBaseSettings):
    """Monitoring and observability settings"""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "midnight"
    LOG_RETENTION: int = 30  # days

    # Metrics
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 8090
    PROMETHEUS_PATH: str = "/metrics"

    # Health Checks
    HEALTH_CHECK_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_TIMEOUT: int = 10
    HEALTH_CHECK_PATH: str = "/health"

    # Tracing
    ENABLE_TRACING: bool = False
    JAEGER_AGENT_HOST: Optional[str] = None
    JAEGER_AGENT_PORT: int = 6831
    TRACE_SAMPLE_RATE: float = 0.1

    # Error Tracking
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    class Config:
        env_prefix = "MONITORING_"
        case_sensitive = True


class EmailSettings(PydanticBaseSettings):
    """Email configuration settings"""

    # SendGrid Configuration
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: Optional[EmailStr] = None
    SENDGRID_FROM_NAME: Optional[str] = None

    # Email Settings
    EMAILS_ENABLED: bool = False
    EMAIL_TEMPLATES_DIR: str = "app/templates/email"
    EMAIL_TEMPLATES_ENABLED: bool = True
    EMAIL_TEST_USER: EmailStr = "test@example.com"

    # Notification Settings
    EMAIL_NOTIFICATION_RETRIES: int = 3
    EMAIL_BATCH_SIZE: int = 10
    EMAIL_BATCH_DELAY: float = 1.0

    @field_validator("EMAILS_ENABLED", mode="before")  # type: ignore
    @classmethod
    def get_emails_enabled(cls, v: bool, info: ValidationInfo) -> bool:
        values: Dict[str, Any] = info.data if info.data else {}
        return bool(
            values.get("SENDGRID_API_KEY") and values.get("SENDGRID_FROM_EMAIL")
        )

    @field_validator("SENDGRID_FROM_NAME", mode="before")  # type: ignore
    @classmethod
    def get_sendgrid_from_name(
        cls, v: Optional[str], info: ValidationInfo
    ) -> Optional[str]:
        if v:
            return v
        return "Evently"

    class Config:
        env_prefix = "EMAIL_"
        case_sensitive = True


class Settings(PydanticBaseSettings):
    """Main application settings"""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    TESTING: bool = False
    VERSION: str = "1.0.0"

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Evently"
    PROJECT_DESCRIPTION: str = "Advanced Event Management Platform"

    # Server Configuration
    SERVER_NAME: str = "evently"
    import os

    SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT: int = 8000
    SERVER_WORKERS: int = 1

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALLOWED_HOSTS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")  # type: ignore
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # User Management
    FIRST_SUPERUSER: EmailStr = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "changeme"
    USERS_OPEN_REGISTRATION: bool = False

    # Feature Flags
    NOTIFICATIONS_ENABLED: bool = True
    NOTIFICATION_RETENTION_DAYS: int = 90
    NOTIFICATION_BATCH_SIZE: int = 100
    PUSH_NOTIFICATIONS_ENABLED: bool = False

    # Component Settings
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    security: SecuritySettings = SecuritySettings()
    scalability: ScalabilitySettings = ScalabilitySettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    email: EmailSettings = EmailSettings()

    # Legacy compatibility - map old settings to new structure
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self.database.database_url

    @property
    def REDIS_URL(self) -> str:
        return self.redis.redis_url

    @property
    def SECRET_KEY(self) -> str:
        return self.security.SECRET_KEY

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.security.ACCESS_TOKEN_EXPIRE_MINUTES

    class Config:
        env_file = ".env"
        case_sensitive = True
        validate_assignment = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export for backward compatibility
settings = get_settings()
