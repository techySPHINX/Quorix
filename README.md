# Quorix

Quorix is an event booking and notification microservice built with FastAPI, SQLAlchemy and Celery.

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fastapi?label=python)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/tests-pytest-blue)](https://docs.pytest.org/)

## Quick overview

- API built with FastAPI
- SQLAlchemy ORM for data models and migrations via Alembic
- Celery for background task processing
- Redis (recommended) for caching and Celery broker (optional)

## System design summary

This repository includes a detailed system design document covering concurrency controls, database modeling, scalability patterns, API design, and optional features (waitlists, seat-level booking, notifications, analytics).

See [System Design](docs/SYSTEM_DESIGN.md) for the full design, diagrams, and engineering tradeoffs.

## Table of contents

- Installation
- Environment
- Running locally
- Running tests
- Contribution guide
- Project structure
- Troubleshooting

## Installation

Prerequisites

- Python 3.11+ (3.12 compatible)
- Redis (optional for local dev)

Create a virtual environment and install dependencies:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

Note: In CI and tests the project uses safe defaults and an in-memory SQLite DB to make test runs fast and reliable.

## Environment variables

The project reads configuration from environment variables (and a `.env` file). The following variables are used by `app/core/config.py`.

- SERVER_NAME (default: `quorix`)
- SERVER_HOST (default: `http://localhost`)
- PROJECT_NAME (default: `Evently`)
- SQLALCHEMY_DATABASE_URI (default: `sqlite+pysqlite:///:memory:`)
- REDIS_URL (default: `redis://localhost:6379/0`)
- CELERY_BROKER_URL (default: `memory://`)
- CELERY_RESULT_BACKEND (default: `rpc://`)
- SENDGRID_API_KEY
- SENDGRID_FROM_EMAIL
- FIRST_SUPERUSER (default: `admin@example.com`)
- FIRST_SUPERUSER_PASSWORD (default: `changeme`)

Set any of these in a `.env` file at the repo root or in your CI secrets for production.

## Running locally

Start Redis (optional) and run the API:

```powershell
# Start uvicorn
.\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run Celery worker (optional):

```powershell
.\.venv\Scripts\Activate.ps1; celery -A app.celery_app.celery worker -Q default,email,notifications -l info
```

## Running tests

Tests use pytest. Run:

```powershell
.\.venv\Scripts\Activate.ps1; pytest -q
```

The test suite runs quickly using an in-memory SQLite DB by default.

## Contribution guide

- Fork the repo
- Create a feature branch: `git checkout -b feat/your-feature`
- Run tests and linters locally
- Open a pull request with a clear description and link to any relevant issue

Please follow the existing code style and add tests for new behavior. Use small, focused commits.

## Project structure (high level)

- `app/` - application code (models, schemas, API endpoints)
- `alembic/` - database migrations
- `tests/` - test suite

## Troubleshooting

- If pydantic raises missing field errors during import, ensure environment variables are set or rely on defaults during development/CI. For production, provide explicit values in your environment or a `.env` file.

## License

MIT
