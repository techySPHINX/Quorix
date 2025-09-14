from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy.pool.base import _ConnectionFairy, _ConnectionRecord

from app.core.config import settings

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "poolclass": NullPool,
    "echo": getattr(settings, "DEBUG", False),
    "connect_args": {
        "command_timeout": 60,
        "server_settings": {
            "application_name": "quorix_app",
        },
    },
}

engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI).replace(
        "postgresql://", "postgresql+asyncpg://"
    ),
    **engine_kwargs,
)

SessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Alias for use in tasks
async_session_maker = SessionLocal

Base = declarative_base()


# --- Connection event listeners (sync-level, for DBAPI connections) ---
@event.listens_for(engine.sync_engine, "connect")  # type: ignore[misc]
def set_postgres_settings(
    dbapi_connection: Any, connection_record: _ConnectionRecord
) -> None:
    """Set PostgreSQL-specific performance settings on new connections."""
    if "postgresql" in str(engine.url):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '60s'")
            cursor.execute("SET lock_timeout = '30s'")
            cursor.execute("SET idle_in_transaction_session_timeout = '10min'")


@event.listens_for(engine.sync_engine, "checkout")  # type: ignore[misc]
def receive_checkout(
    dbapi_connection: Any,
    connection_record: _ConnectionRecord,
    connection_proxy: _ConnectionFairy,
) -> None:
    """Triggered when a connection is checked out from the pool."""
    pass  # Add logging/monitoring if needed


@event.listens_for(engine.sync_engine, "checkin")  # type: ignore[misc]
def receive_checkin(
    dbapi_connection: Any, connection_record: _ConnectionRecord
) -> None:
    """Triggered when a connection is returned to the pool."""
    pass  # Add logging/monitoring if needed
