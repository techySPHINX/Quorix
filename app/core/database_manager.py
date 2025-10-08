"""
Enhanced Database Management with Advanced Connection Pooling
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import event, text
from sqlalchemy.exc import DisconnectionError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DatabaseManager:
    """Advanced database manager with connection pooling and health monitoring"""

    def __init__(self) -> None:
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self._setup_engine()

    def _setup_engine(self) -> None:
        """Setup database engine with advanced configuration"""
        # Determine database URL and driver
        db_url = self._prepare_database_url()

        # Configure engine parameters based on database type
        engine_kwargs = self._get_engine_kwargs(db_url)

        # Create engine
        self.engine = create_async_engine(db_url, **engine_kwargs)

        # Setup session factory
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        # Setup event listeners
        self._setup_event_listeners()

        logger.info(f"Database engine initialized with URL: {self._mask_url(db_url)}")

    def _prepare_database_url(self) -> str:
        """Prepare database URL with appropriate async driver"""
        raw_url = settings.database.database_url

        # Handle SQLite for testing
        if settings.TESTING:
            return "sqlite+aiosqlite:///:memory:"

        # Handle PostgreSQL
        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif raw_url.startswith("postgresql+asyncpg://"):
            return raw_url

        return raw_url

    def _get_engine_kwargs(self, db_url: str) -> Dict[str, Any]:
        """Get engine configuration based on database type"""
        base_kwargs: Dict[str, Any] = {}
        base_kwargs["echo"] = settings.database.DB_ECHO
        base_kwargs["future"] = True
        base_kwargs["pool_pre_ping"] = settings.database.DB_POOL_PRE_PING
        base_kwargs["pool_recycle"] = settings.database.DB_POOL_RECYCLE

        if "sqlite" in db_url:
            # SQLite configuration
            sqlite_connect_args: Dict[str, Any] = {
                "check_same_thread": False,
                "timeout": 20,
            }
            base_kwargs.update(
                {
                    "poolclass": StaticPool,
                    "connect_args": sqlite_connect_args,
                }
            )
        else:
            # PostgreSQL configuration
            postgres_server_settings: Dict[str, str] = {
                "application_name": f"{settings.PROJECT_NAME}_app",
                "statement_timeout": str(settings.database.DB_STATEMENT_TIMEOUT),
                "lock_timeout": str(settings.database.DB_LOCK_TIMEOUT),
                "idle_in_transaction_session_timeout": str(
                    settings.database.DB_IDLE_IN_TRANSACTION_TIMEOUT
                ),
            }
            postgres_connect_args: Dict[str, Any] = {
                "command_timeout": settings.database.DB_COMMAND_TIMEOUT,
                "server_settings": postgres_server_settings,
            }
            base_kwargs.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": settings.database.DB_POOL_SIZE,
                    "max_overflow": settings.database.DB_MAX_OVERFLOW,
                    "pool_timeout": settings.database.DB_POOL_TIMEOUT,
                    "connect_args": postgres_connect_args,
                }
            )

        return base_kwargs

    def _setup_event_listeners(self) -> None:
        """Setup database event listeners for monitoring and optimization"""
        if not self.engine:
            return

        @event.listens_for(self.engine.sync_engine, "connect")  # type: ignore
        def set_postgres_settings(
            dbapi_connection: Any, connection_record: Any
        ) -> None:
            """Set PostgreSQL-specific performance settings on new connections"""
            engine_url = getattr(self.engine, "url", None)
            if engine_url and "postgresql" in str(engine_url):
                with dbapi_connection.cursor() as cursor:
                    try:
                        # Performance optimizations
                        cursor.execute(
                            "SET statement_timeout = %s",
                            (settings.database.DB_STATEMENT_TIMEOUT,),
                        )
                        cursor.execute(
                            "SET lock_timeout = %s",
                            (settings.database.DB_LOCK_TIMEOUT,),
                        )
                        cursor.execute(
                            "SET idle_in_transaction_session_timeout = %s",
                            (settings.database.DB_IDLE_IN_TRANSACTION_TIMEOUT,),
                        )

                        # Additional optimizations
                        cursor.execute("SET synchronous_commit = 'on'")
                        cursor.execute("SET work_mem = '4MB'")
                        cursor.execute("SET maintenance_work_mem = '64MB'")

                        logger.debug("PostgreSQL connection optimized")
                    except Exception as e:
                        logger.warning(f"Failed to set PostgreSQL settings: {e}")

        @event.listens_for(self.engine.sync_engine, "checkout")  # type: ignore
        def receive_checkout(
            dbapi_connection: Any, connection_record: Any, connection_proxy: Any
        ) -> None:
            """Monitor connection checkout"""
            connection_record.info["checkout_time"] = time.time()
            logger.debug("Database connection checked out")

        @event.listens_for(self.engine.sync_engine, "checkin")  # type: ignore
        def receive_checkin(dbapi_connection: Any, connection_record: Any) -> None:
            """Monitor connection checkin"""
            if "checkout_time" in connection_record.info:
                checkout_duration = (
                    time.time() - connection_record.info["checkout_time"]
                )
                if checkout_duration > 30:  # Log slow connections
                    logger.warning(
                        f"Long-running database connection: {checkout_duration:.2f}s"
                    )
            logger.debug("Database connection checked in")

        @event.listens_for(self.engine.sync_engine, "invalidate")  # type: ignore
        def receive_invalidate(
            dbapi_connection: Any, connection_record: Any, exception: Any
        ) -> None:
            """Handle connection invalidation"""
            logger.warning(f"Database connection invalidated: {exception}")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with proper error handling"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")

        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive database health check"""
        if not self.engine:
            return {"status": "error", "message": "Database engine not initialized"}

        try:
            start_time = time.time()

            async with self.get_session() as session:
                # Test basic connectivity
                result = await session.execute(text("SELECT 1 as health_check"))
                health_result = result.scalar()

                if health_result != 1:
                    return {"status": "error", "message": "Health check query failed"}

                # Test transaction capability
                await session.execute(text("SELECT NOW()"))

                response_time = (time.time() - start_time) * 1000  # Convert to ms

                # Get pool status if available
                pool_status = {}
                pool = getattr(self.engine, "pool", None)
                if pool:
                    pool_status = {
                        "pool_size": getattr(pool, "size", lambda: None)(),
                        "checked_in": getattr(pool, "checkedin", lambda: None)(),
                        "checked_out": getattr(pool, "checkedout", lambda: None)(),
                        "overflow": getattr(pool, "overflow", None),
                        "invalid": getattr(pool, "invalid", None),
                    }

                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "pool_status": pool_status,
                    "database_url": self._mask_url(str(self.engine.url)),
                }

        except DisconnectionError as e:
            logger.error(f"Database disconnection error: {e}")
            return {"status": "error", "message": "Database disconnected"}
        except SQLAlchemyError as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            return {"status": "error", "message": "Unexpected error"}

    async def get_pool_status(self) -> dict[str, Any]:
        """Get detailed connection pool status"""
        if not self.engine or not hasattr(self.engine, "pool"):
            return {"error": "Pool information not available"}

        pool = self.engine.pool
        return {
            "pool_size": getattr(pool, "size", lambda: None)(),
            "checked_in": getattr(pool, "checkedin", lambda: None)(),
            "checked_out": getattr(pool, "checkedout", lambda: None)(),
            "overflow": getattr(pool, "overflow", None),
            "invalid": getattr(pool, "invalid", None),
            "pool_class": pool.__class__.__name__,
        }

    async def close(self) -> None:
        """Close database engine and all connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database engine closed")

    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL"""
        if "@" in url:
            parts = url.split("@")
            if len(parts) == 2:
                # Mask password
                auth_part = parts[0]
                if ":" in auth_part:
                    protocol_user = auth_part.rsplit(":", 1)[0]
                    return f"{protocol_user}:***@{parts[1]}"
        return url


# Global database manager instance
db_manager = DatabaseManager()

# SQLAlchemy declarative base
Base = declarative_base()

# FastAPI dependency for getting database sessions


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions"""
    async with db_manager.get_session() as session:
        yield session


# Legacy compatibility - keep the old engine and SessionLocal
engine = db_manager.engine
SessionLocal = db_manager.session_factory
async_session_maker = db_manager.session_factory
