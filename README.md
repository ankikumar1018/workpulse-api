<div align="center">

<h1>WorkPulse API</h1>

FastAPI backend for workforce communication automation.

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Ruff](https://img.shields.io/badge/Lint-Ruff-4444DD?style=for-the-badge)
![Pytest](https://img.shields.io/badge/Tested_with-pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

</div>

> Status: Foundation complete. Core domain features are being implemented.

## Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Guide](#setup-guide)
- [Developer Workflow](#developer-workflow)
- [Contribution Guide](#contribution-guide)
- [Documentation](#documentation)
- [Notes](#notes)
- [License](#license)

## Overview

WorkPulse API is the system of record for workforce communication workflows:

- Organization and worker hierarchy management
- Work item lifecycle tracking
- Template-driven messaging flows
- Delivery visibility and auditability

## Architecture

The project follows a layered modular monolith:

- API layer: request/response contracts and routing
- Application layer: orchestration and use-case logic
- Domain layer: business rules and entities
- Infrastructure layer: database and external integrations
- Workers layer: async/background processing and webhooks

## Tech Stack

| Area | Choice |
|---|---|
| Runtime | Python 3.14 |
| API | FastAPI |
| Database | PostgreSQL + SQLAlchemy 2.x |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Package Management | uv |
| Lint/Format | Ruff, Black, isort |
| Type Checking | mypy |
| Testing | pytest + pytest-asyncio |

## Project Structure

```text
app/
  api/             # HTTP routes and schemas
  application/     # use-case orchestration
  domain/          # business rules and entities
  infrastructure/  # DB/external adapters/providers
  workers/         # async jobs and webhook handlers
alembic/           # database migrations
tests/             # automated test suite
```

## Setup Guide

### Prerequisites

- Python 3.14+
- Docker Desktop
- uv

Install uv (Windows PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Install uv (macOS/Linux):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 1) Install Dependencies

```bash
uv sync --group dev
```

### 2) Configure Environment

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Update `.env` values for local development as needed.

### 3) Start Database

```bash
docker compose up -d postgres
```

### 4) Apply Migrations

```bash
uv run alembic upgrade head
```

### 5) Run the API

```bash
uv run fastapi dev app/main.py --port 8000
```

### 6) Verify

- API docs: http://127.0.0.1:8000/docs
- Alternative docs: http://127.0.0.1:8000/redoc
- Health endpoint: http://127.0.0.1:8000/health

## Developer Workflow

### Daily Commands

```bash
# run tests
uv run pytest

# lint and quality
uv run ruff check .
uv run black --check app tests
uv run isort --check app tests
uv run mypy app

# auto-fix lint findings
uv run ruff check --fix .
```

### Common Migration Commands

After changing SQLAlchemy models, run these commands from the backend root. Ensure
PostgreSQL is running and `DATABASE_URL` points to the target database.

```powershell
docker compose up -d postgres
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/workpulse"
```

```bash
# verify whether model changes need a migration
uv run alembic check

# generate a migration from the model metadata
uv run alembic revision --autogenerate -m "Describe change"

# review the generated file in alembic/versions/ before applying it

# apply all pending migrations
uv run alembic upgrade head

# rollback one migration
uv run alembic downgrade -1
```

On Windows, if `uv run alembic` selects the wrong environment, use
`.venv\Scripts\alembic.exe` from the backend repository instead.

On macOS/Linux, use `.venv/bin/alembic` if the environment is activated or
`uv run alembic` resolves to the wrong Python environment.

## Contribution Guide

### Branching

- Create feature/fix branch from main:
  - `feat/<short-name>`
  - `fix/<short-name>`

### Before Opening a PR

Run all checks locally:

```bash
uv run ruff check .
uv run black --check app tests
uv run isort --check app tests
uv run mypy app
uv run pytest
```

### PR Expectations

- Keep scope focused and incremental
- Add or update tests for behavior changes
- Include migration notes for schema changes
- Use clear commit messages and PR descriptions

## Documentation

- [Development Setup Guide](docs/DEVELOPMENT.md)
- [Initial Setup Summary](docs/SETUP_COMPLETE.md)

## Notes

- `htmlcov/` is a local coverage artifact and is ignored by Git.
- Prefer `docker compose` over legacy `docker-compose`.

## License

MIT
