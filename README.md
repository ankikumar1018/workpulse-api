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

## Authentication and User Management

Authentication uses short-lived JWT access tokens and rotatable, revocable
refresh tokens. Refresh-token hashes are stored in PostgreSQL; raw refresh
tokens are never persisted.

Available endpoints:

- `POST /api/v1/auth/token` — OAuth2 password-form login using the email as `username`.
- `POST /api/v1/auth/refresh` — rotate a refresh token and receive a new token pair.
- `POST /api/v1/users` — create an administrator in the current organization.
- `GET /api/v1/users` — list administrators in the current organization.
- `GET/PATCH /api/v1/users/{user_id}` — retrieve or update an administrator.

User lifecycle states are `active` and `inactive`; inactive users cannot log in,
refresh tokens, or access protected API routes. All user-management endpoints
require an active administrator bearer token and enforce organization scoping.

Project management endpoints require an active administrator bearer token and
enforce organization scoping. `GET /api/v1/projects/{project_id}` returns
archived projects for history, while archived projects cannot be modified.
`DELETE /api/v1/projects/{project_id}` archives the project rather than
physically deleting it.

Department management is available through the project-nested endpoints
`/api/v1/projects/{project_id}/departments` for creation and listing, and
`/api/v1/departments/{department_id}` for retrieval, updates, and archival.
Department operations validate project ownership and reject mutations under
archived projects. Departments now also support `primary_contact_worker_id`
updates with strict validation: the selected worker must belong to the same
department, remain active, and be organization-scoped.

Worker management is available through `/api/v1/departments/{department_id}/workers`
for creation and listing, and `/api/v1/workers/{worker_id}` for retrieval,
updates, and deactivation. Worker operations validate department and project
ownership, require E.164 phone numbers, enforce organization-wide phone
uniqueness, and reject new workers under archived projects or departments.
Worker payloads normalize phone input to E.164, persist an explicit contact
channel (`whatsapp` in MVP), and enforce consent status (`opted_in` or
`opted_out`). Inactive or opted-out workers are blocked from communication
recipient workflows.

Department worker assignment lifecycle management is available through
`POST /api/v1/departments/{department_id}/workers/{worker_id}/assignment` and
`DELETE /api/v1/departments/{department_id}/workers/{worker_id}/assignment`.
Assignment changes are organization-scoped, require active target departments,
reject inactive workers as new assignment recipients, and mark removed
assignments as inactive to keep communication recipients valid.

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
  api/             # HTTP routes, dependencies, and errors
  application/     # use-case orchestration
  domain/          # business rules and entities
  infrastructure/  # DB/external adapters/providers
  schemas/         # request and response contracts
  workers/         # async jobs and webhook handlers
alembic/           # database migrations
tests/             # automated test suite
```

## Setup Guide

### Prerequisites

- Docker Desktop with Docker Compose v2

Python, uv, PostgreSQL, and project dependencies are installed inside the
Docker image. Do not install or run the backend directly on the host.

### 1) Build the Images

```bash
docker compose build api
```

The API image is production-focused. The test image contains the development
tools and is built automatically when needed.

### 2) Start the API

```bash
docker compose up --build -d postgres api
```

The API waits for PostgreSQL and migrations, then starts on port `8000`.

### 3) Run Tests and Quality Checks

```bash
docker compose --profile test run --rm test
bash scripts/format.sh
```

Both commands run inside Docker. The first runs pytest; the second runs Ruff,
Black, isort, and mypy.

### 4) Verify

- API docs: http://127.0.0.1:8000/docs
- Alternative docs: http://127.0.0.1:8000/redoc
- Health endpoint: http://127.0.0.1:8000/health

Stop the stack when finished:

```bash
docker compose down
```

Add `--volumes` when you intentionally want to remove the local PostgreSQL
data volume.

## Developer Workflow

### Daily Commands

```bash
# run tests
docker compose --profile test run --rm test

# run Ruff, Black, isort, and mypy checks
bash scripts/format.sh
```

### Common Migration Commands

After changing SQLAlchemy models, run these commands through the API container.
The container reaches PostgreSQL using the Compose service name `postgres`.

```bash
# verify whether model changes need a migration
docker compose run --rm api alembic check

# generate a migration from the model metadata
docker compose run --rm api alembic revision --autogenerate -m "Describe change"

# review the generated file in alembic/versions/ before applying it

# apply all pending migrations
docker compose run --rm api alembic upgrade head

# rollback one migration
docker compose run --rm api alembic downgrade -1
```

## Contribution Guide

### Branching

- Create feature/fix branch from main:
  - `feat/<short-name>`
  - `fix/<short-name>`

### Before Opening a PR

Run the checks before opening a PR:

```bash
bash scripts/format.sh
docker compose --profile test run --rm test
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
- Docker Compose is the supported execution environment for the API, migrations,
  quality checks, and tests.

## License

MIT
