from contextlib import asynccontextmanager
import re
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import Result
from sqlalchemy.dialects.postgresql import insert as pg_insert

T = TypeVar('T', bound=DeclarativeBase)


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    max_page_size: int = 100

    def __post_init__(self) -> None:
        if self.page < 1:
            self.page = 1
        if self.page_size > self.max_page_size:
            self.page_size = self.max_page_size
        if self.page_size < 1:
            self.page_size = 1

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: List[Any], total: int, pagination: PaginationParams) -> "PaginatedResponse":
        pages = (total + pagination.page_size - 1) // pagination.page_size
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            pages=pages
        )


@asynccontextmanager
async def db_transaction(db: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    try:
        yield db
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e


async def execute_with_retry(
    db: AsyncSession,
    query_func: Callable[..., Any],
    max_retries: int = 3,
    *args: Any,
    **kwargs: Any
) -> Any:
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            return await query_func(db, *args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                error_msg = str(e).lower()
                retryable_errors = [
                    'connection', 'timeout', 'deadlock', 'serialization failure'
                ]

                if any(err in error_msg for err in retryable_errors):
                    await db.rollback()
                    continue
                else:
                    raise
            else:
                raise

    # mypy might complain here, but this is safe
    raise last_exception  # type: ignore


def _validate_identifier(name: str) -> str:
    """Validate simple SQL identifiers to mitigate injection when binding identifiers.

    We only allow [A-Za-z_][A-Za-z0-9_]* which covers typical table/index names.
    """
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


async def bulk_insert_or_update(
    db: AsyncSession,
    model: Type[T],
    data: List[Dict[str, Any]],
    conflict_columns: List[str],
    update_columns: Optional[List[str]] = None,
    batch_size: int = 1000,
) -> int:
    if not data:
        return 0

    # Validate table name and column names
    table = model.__table__
    _ = _validate_identifier(model.__tablename__)
    model_columns = {col.name for col in table.columns}

    affected_rows = 0
    for i in range(0, len(data), batch_size):
        batch = data[i: i + batch_size]
        if not batch:
            continue

        # Ensure only known columns are present
        unknown_keys = set(batch[0].keys()) - model_columns
        if unknown_keys:
            raise ValueError(f"Unknown columns in batch: {unknown_keys}")

        # Compute update columns for this batch if not provided
        if update_columns is None:
            all_columns = set(batch[0].keys())
            pk_columns = {col.name for col in table.primary_key}
            conflict_set = set(conflict_columns)
            local_update_columns = list(all_columns - pk_columns - conflict_set)
        else:
            local_update_columns = list(update_columns)

        # Validate conflict/update columns
        invalid_conflicts = set(conflict_columns) - model_columns
        if invalid_conflicts:
            raise ValueError(f"Invalid conflict columns: {invalid_conflicts}")
        invalid_updates = set(local_update_columns) - model_columns
        if invalid_updates:
            raise ValueError(f"Invalid update columns: {invalid_updates}")

        stmt = pg_insert(table).values(batch)
        if local_update_columns:
            stmt = stmt.on_conflict_do_update(
                index_elements=[table.c[c] for c in conflict_columns],
                set_={c: getattr(stmt.excluded, c) for c in local_update_columns},
            )

        result: Result[Any] = await db.execute(stmt)
        affected_rows += getattr(result, "rowcount", 0) or 0

    await db.commit()
    return affected_rows


async def get_table_stats(db: AsyncSession, table_name: str) -> Dict[str, Any]:
    stats: Dict[str, Any] = {}

    safe_table = _validate_identifier(table_name)
    # Cannot bind identifiers; validated name is used
    result: Result[Any] = await db.execute(
        text(f"SELECT COUNT(*) as count FROM {safe_table}")  # nosec B608
    )
    stats["row_count"] = result.scalar()

    try:
        # Parameterized function call
        result = await db.execute(
            text("SELECT pg_total_relation_size(:t) as size"), {"t": safe_table}
        )
        stats["size_bytes"] = result.scalar()
    except Exception:
        stats["size_bytes"] = None

    try:
        result = await db.execute(
            text(
                """
                SELECT 
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE relname = :t
                """
            ),
            {"t": safe_table},
        )
        stats["index_usage"] = [dict(row) for row in result]
    except Exception:
        stats["index_usage"] = []

    return stats


async def optimize_table(db: AsyncSession, table_name: str) -> bool:
    try:
        safe_table = _validate_identifier(table_name)
        # VACUUM cannot bind table identifiers; validated identifier used
        await db.execute(text(f"VACUUM ANALYZE {safe_table}"))  # nosec B608
        await db.commit()
        return True
    except Exception:
        await db.rollback()
        return False


class DatabaseHealthCheck:
    @staticmethod
    async def check_connection(db: AsyncSession) -> bool:
        try:
            await db.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @staticmethod
    async def get_connection_pool_status(engine) -> Dict[str, Any]:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow(),
        }

    @staticmethod
    async def get_slow_queries(db: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                text(
                    """
                    SELECT 
                        query,
                        mean_exec_time,
                        calls,
                        total_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements 
                    ORDER BY mean_exec_time DESC 
                    LIMIT :limit
                    """
                ),
                {"limit": int(limit)},
            )
            return [dict(row) for row in result]
        except Exception:
            return []
