from typing import Any
from typing import Any as _Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

engine_kwargs = {
    "pool_pre_ping": True,
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "poolclass": NullPool,
    "echo": getattr(settings, "DEBUG", False),
}

# Prepare the DB URL so that async drivers are used when required by SQLAlchemy
raw_db_url = str(settings.SQLALCHEMY_DATABASE_URI)

# If using SQLite and the URL doesn't already specify an async driver, prefer aiosqlite
if raw_db_url.startswith("sqlite://") and "+aiosqlite" not in raw_db_url:
    db_url = raw_db_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
elif raw_db_url.startswith("postgresql://") and "+asyncpg" not in raw_db_url:
    db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    db_url = raw_db_url

if "sqlite" in db_url:
    # aiosqlite doesn't require server settings; reduce connect_args for sqlite
    engine_kwargs.setdefault("connect_args", {})
else:
    engine_kwargs.setdefault("connect_args", {})
    engine_kwargs["connect_args"].update(
        {
            "command_timeout": 60,
            "server_settings": {"application_name": "quorix_app"},
        }
    )

engine = create_async_engine(db_url, **engine_kwargs)

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
def set_postgres_settings(dbapi_connection: Any, connection_record: _Any) -> None:
    """Set PostgreSQL-specific performance settings on new connections."""
    if "postgresql" in str(engine.url):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '60s'")
            cursor.execute("SET lock_timeout = '30s'")
            cursor.execute("SET idle_in_transaction_session_timeout = '10min'")


@event.listens_for(engine.sync_engine, "checkout")  # type: ignore[misc]
def receive_checkout(
    dbapi_connection: Any,
    connection_record: _Any,
    connection_proxy: _Any,
) -> None:
    """Triggered when a connection is checked out from the pool."""
    pass  # Add logging/monitoring if needed


@event.listens_for(engine.sync_engine, "checkin")  # type: ignore[misc]
def receive_checkin(dbapi_connection: Any, connection_record: _Any) -> None:
    """Triggered when a connection is returned to the pool."""
    pass  # Add logging/monitoring if needed
