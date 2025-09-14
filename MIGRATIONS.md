# Database Migrations (Alembic)

This project uses Alembic for schema migrations. The configuration lives in `alembic/` and is wired to the SQLAlchemy models via `app.database.Base`.

Alembic loads the database URL in this order:

1. `-x dburl=...` CLI extra argument (recommended for safety)
2. `sqlalchemy.url` in `alembic.ini` (we keep it empty by default)
3. `SQLALCHEMY_DATABASE_URI` from `.env`

## Common commands (PowerShell)

- Create a new migration (autogenerate):

```powershell
# using .env URL
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic revision --autogenerate -m "add something"

# or explicitly target a DB URL (safer for prod):
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic -x dburl="postgresql://user:pass@host:5432/dbname" revision --autogenerate -m "add something"
```

- Upgrade to latest (head):

```powershell
# using .env URL
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic upgrade head

# explicit URL override
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic -x dburl="postgresql://user:pass@host:5432/dbname" upgrade head
```

- Downgrade one revision:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic downgrade -1
```

- View current revision:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic current
```

- Show history:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic history --verbose
```

## Notes

- Async engine: Alembic is configured to use `asyncpg` for Postgres. If your URL contains `sslmode=require`, Alembic strips it and enables SSL via connect args.
- Multiple Bases: All models now inherit from `app.database.Base`. If you add a new model, ensure it imports and uses this Base.
- Safety: Never run migrations against production accidentally. Prefer the `-x dburl=...` form for production and verify the target before running `upgrade`.
- Templates: Generated revision files start with empty `upgrade()`/`downgrade()` functions. Autogenerate populates them based on detected changes—always review before applying.

# Database migrations with Alembic

This project uses Alembic to manage schema migrations for the PostgreSQL database.

## Prerequisites

- Ensure dependencies are installed (see `requirements.txt`).
- Configure your `.env` with a safe database URL. For local dev, prefer a local DB instead of production.

## Common commands (PowerShell)

- Create a new migration (autogenerate):

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic revision --autogenerate -m "<message>"
```

- Apply migrations (upgrade to latest):

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic upgrade head
```

- Downgrade one step:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic downgrade -1
```

- Show current migration:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic current
```

- Show history:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic history --verbose
```

## Safety: target a specific DB

By default, Alembic uses `SQLALCHEMY_DATABASE_URI` from `.env`. To override the target database at runtime (e.g., to avoid touching production), use `-x dburl=...`:

```powershell
$env:PYTHONPATH = (Resolve-Path .).Path; python -m alembic upgrade head -x dburl="postgresql://user:pass@localhost:5432/evently"
```

Note: Async is handled automatically; sync URLs (postgresql://) will be adapted to `postgresql+asyncpg://` internally. Query param `sslmode` is stripped for asyncpg and SSL is enabled for managed providers.

## Troubleshooting

- If autogenerate misses changes, ensure all model modules are imported in `app/models/__init__.py` (they are) and Alembic's `env.py` can import them.
- If you see connection errors related to `sslmode` with asyncpg, the env is already configured to drop it and enforce SSL.
- If you changed model base classes, add their `metadata` to `TARGET_METADATAS` in `alembic/env.py`.
