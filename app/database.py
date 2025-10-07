"""
Database configuration with enhanced connection pooling and management.
This file maintains backward compatibility while using the new database manager.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

# Provide Base for ORM models (for mypy and model imports)
# Import enhanced database components
from app.core.database_manager import Base as _Base
from app.core.database_manager import db_manager

Base = _Base

# Export for backward compatibility
engine = db_manager.engine
SessionLocal = db_manager.session_factory
async_session_maker = db_manager.session_factory

# Export for backward compatibility
engine = db_manager.engine
SessionLocal = db_manager.session_factory
async_session_maker = db_manager.session_factory


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Legacy database dependency function"""
    async with db_manager.get_session() as session:
        yield session
