from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from alembic import context
from sqlalchemy import MetaData, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Ensure app package is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load app modules after fixing sys.path using imperative imports to avoid
# flake8 E402/F401 warnings in this env script. Use __import__ so these
# are not treated as top-level static import statements by linters.
__import__("app.models")
settings = __import__("app.core.config", fromlist=["settings"]).settings
ModelBase = __import__("app.database", fromlist=["Base"]).Base

# Single metadata for all models
TARGET_METADATA = ModelBase.metadata

config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Optionally set sqlalchemy.url for alembic when invoked without env vars


def _normalize_db_url(url: str) -> str:
    # Convert sync URL to async if needed and drop unsupported query args
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    parsed = urlparse(url)
    if parsed.query:
        # Drop query params that asyncpg.connect doesn't accept as kwargs
        unsupported = {"sslmode", "channel_binding"}
        q = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in unsupported
        ]
        url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(q),
                parsed.fragment,
            )
        )
    return url


# Prefer a db URL passed via `-x dburl=...`, then existing alembic.ini value, then settings
x_args = context.get_x_argument(as_dictionary=True)
override_url = x_args.get("dburl") if isinstance(x_args, dict) else None
if override_url:
    config.set_main_option("sqlalchemy.url", _normalize_db_url(str(override_url)))
elif not config.get_main_option("sqlalchemy.url"):
    config.set_main_option(
        "sqlalchemy.url", _normalize_db_url(str(settings.SQLALCHEMY_DATABASE_URI))
    )


def get_target_metadata() -> MetaData:
    return TARGET_METADATA


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_target_metadata(),
        render_as_batch=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=get_target_metadata(),
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine | None = None
    url = config.get_main_option("sqlalchemy.url")
    # Enable SSL for asyncpg when connecting to managed Postgres providers like Neon
    connect_args = {}
    if url.startswith("postgresql+asyncpg://"):
        connect_args["ssl"] = True
    connectable = create_async_engine(
        url, poolclass=pool.NullPool, connect_args=connect_args
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
