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
- [WhatsApp Setup](#whatsapp-setup)
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

## WhatsApp Setup

The adapter and signed delivery webhooks are implemented. Scheduled WhatsApp
jobs require an approved provider-template mapping; they never silently fall
back to plain text outside the customer-service window.

### Local Testing (No Meta Account)

Run from the backend root. No credentials, tunnel, API server or database are
required; Compose starts a disposable container with no dependent services.

```powershell
docker compose run --rm --no-deps --build api python -m app.workers.whatsapp_smoke --local
```

Local mode uses the real WhatsApp adapter with HTTPX MockTransport, dummy
credentials and a synthetic recipient. It prints the request type/template and
returns a simulated `wamid.local-test`; no real message or network request is
made, even when real credentials are configured. It cannot be combined with
`--send`. Use `--template`, `--language` and repeated `--parameter` arguments to
exercise custom template payloads.

Simulate failures (these intentionally exit with code 1, without retries):

```powershell
docker compose run --rm --no-deps api python -m app.workers.whatsapp_smoke --local --scenario transient
docker compose run --rm --no-deps api python -m app.workers.whatsapp_smoke --local --scenario permanent
```

Transient simulates HTTP 429; permanent simulates HTTP 400. Local mode does not
produce webhook events, write message records, or check Meta template approval.
Run the offline tests for signed callbacks, failure handling, template mapping,
state transitions, consent checks and duplicate protection:

```powershell
docker compose run --rm --no-deps --build test env -u SECRET_KEY python -m pytest -q --no-cov tests/test_whatsapp_provider.py tests/test_whatsapp_webhooks.py tests/test_message_job_processor.py tests/test_message_lifecycle.py tests/test_templates.py
```

These tests use isolated collaborators, not the shared database. The temporary
secret override removal is only for a default-settings test, never the API.
Local success does not prove Meta connectivity or automatic schedule execution;
the live setup below is a separate acceptance step.

### PostgreSQL End-to-End Dry Run

This opt-in test uses real repositories, template rendering, job processing,
message persistence and the signed HTTP webhook route. Meta HTTP calls are
mocked and network transport is blocked. It verifies current work-item state,
exactly one dispatch, job completion, duplicate/out-of-order callbacks, persisted
delivery history and cross-tenant rejection. It rolls back its test transaction.
Without `--whatsapp-test-db-url` the test is skipped; the supplied database name
must start with `workpulse_test`. Never point it at a shared or production DB.

For Docker Desktop on Windows, run from the backend root. These example
credentials are only for the disposable database, which has no persistent volume:

```powershell
docker run --rm -d --name workpulse-whatsapp-review-db -p 127.0.0.1:55439:5432 -e POSTGRES_DB=workpulse_test_whatsapp -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=local-dry-run-only postgres:18-alpine
docker exec workpulse-whatsapp-review-db pg_isready -U postgres
docker compose run --rm --no-deps -e DB_HOST=host.docker.internal -e DB_PORT=55439 -e DB_NAME=workpulse_test_whatsapp -e DB_USER=postgres -e DB_PASSWORD=local-dry-run-only -e DATABASE_URL=postgresql+psycopg://postgres:local-dry-run-only@host.docker.internal:55439/workpulse_test_whatsapp api alembic upgrade head
docker compose run --rm --no-deps --build test env -u SECRET_KEY python -m pytest -q --no-cov --whatsapp-test-db-url postgresql+psycopg://postgres:local-dry-run-only@host.docker.internal:55439/workpulse_test_whatsapp
docker stop workpulse-whatsapp-review-db
```

Wait for `pg_isready` to report accepting connections before migrations. Use a
different free port if 55439 is already taken. Stop the disposable container
even if validation fails; `--rm` removes it after stopping. Run this test in
Docker: Windows' default Proactor event loop is incompatible with Psycopg async
connections. This dry run does not exercise the admin browser, a live cloud
queue, automatic scheduling or real WhatsApp delivery.

### 1. Verify Meta setup

In Meta App Dashboard, open WhatsApp / API Setup (or Use cases / Customize /
API Setup), select the WhatsApp Business Account and test sender, add and verify
your own recipient number, and send the supplied `hello_world` template.
Confirm receipt before connecting WorkPulse. Retain the sender Phone Number ID
(not the actual phone number or Business Account ID).

### 2. Configure backend secrets

Create an ignored `.env` in the backend root with the five WhatsApp settings
shown in `.env.example`. Use the temporary Meta access token for the initial
test, the sender Phone Number ID, and the app secret from Meta app settings.
Choose a separate random webhook verify token. Keep secrets out of git, chat,
frontend variables, screenshots and logs. Docker Compose passes these settings
only to the API service. Do not run `docker compose config` without `--quiet`
when real secrets are present: the expanded configuration includes them.

Run from the backend root:

```powershell
docker compose up --build -d postgres api
docker compose exec -T api python -m app.workers.whatsapp_smoke
```

The second command checks configuration presence only, prints no secret values,
and makes no network request. Recreate the API container after changing `.env`;
restarting the old container does not load changed Compose environment values.

### 3. Configure the webhook

Expose port 8000 through an HTTPS tunnel, for example `ngrok http 8000` if ngrok
is installed and authenticated. Prefer exposing only the webhook path; never
make a development database or debug interface publicly reachable.

Set Meta's callback URL to
`https://<public-host>/api/v1/webhooks/whatsapp`, and use the same verify token
as `WHATSAPP_WEBHOOK_VERIFY_TOKEN`. Verify and save, subscribe to the `messages`
field, and ensure the app is subscribed to the intended WhatsApp Business
Account. A changed tunnel hostname requires updating the callback URL.
The GET handshake returns Meta's challenge; signed POST events return HTTP 200.

### 4. Send one explicit connectivity test

Replace the example recipient with your verified, opted-in test number:

```powershell
docker compose exec -T api python -m app.workers.whatsapp_smoke --send --recipient "+15551234567" --confirm-opt-in
```

This sends exactly one `hello_world` / `en_US` template per invocation. For your
own approved template, add `--template work_update --language en_US`, and repeat
`--parameter "value"` in positional body order. There are no automatic retries.
An accepted `wamid` is not proof of delivery: confirm phone receipt and signed
webhook arrival. The smoke command does not create a WorkPulse message row, so
its delivery events are acknowledged but it does not appear in admin history.

### 5. Map the operational template

Create a body-only, positional-parameter template in WhatsApp Manager and wait
for approval. Keep its exact name, language and static body text aligned with
the WorkPulse template. In `/docs`, authorize as a tenant administrator and use
`PATCH /api/v1/templates/{template_id}` to set:

```json
{
  "provider_template_name": "work_update",
  "provider_template_language": "en_US"
}
```

Example Meta body: `Hi {{1}}, project {{2}} is {{3}}.` Corresponding WorkPulse
body: `Hi {{primary_contact_name}}, project {{project_name}} is {{work_status}}.`
Declare these variables in the WorkPulse variable schema. Parameters use first
placeholder appearance order, not JSON schema order; repeated names reuse the
same parameter. Supported context values are `project_name`, `department_name`,
`date`, `work_status`, `primary_contact_name`, `work_item_title`, `priority`, and
`due_date`; optional values must exist when referenced. Headers, buttons, media
and Meta named parameters are not supported by this adapter yet. Approval is
managed in Meta, not automatically checked by WorkPulse.

### Remaining activation gates

- Replace the temporary token with a securely stored system-user token, assign
  the app and WhatsApp account assets, and grant `whatsapp_business_messaging`
  and `whatsapp_business_management` (plus management permissions required by
  your onboarding flow). Tokens can still be revoked; plan rotation.
- Register/verify the real sender, complete applicable business verification,
  billing and app-publishing requirements, and obtain recipient opt-in.
- Automatic scheduling is not connected end-to-end yet: activation calculates
  `next_run_at_utc`, but a due-schedule producer and authenticated queue execution
  endpoint must be wired to the existing processor before enabling reminders.
- Validate a persisted job through provider acceptance, delivery webhook and
  admin history in a controlled environment; cloud queue tests remain pending.
  Keep schedules paused until these gates pass. Process-local locks and rate
  limits do not guarantee duplicate protection across multiple replicas or
  ambiguous provider timeouts; resolve these before production scaling.

References: [Meta getting started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
and [webhook setup](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks).

Deep preparation validation (2026-10-07): 174 tests pass in Docker including the
opt-in PostgreSQL job-to-delivery dry run on a disposable migrated database.
Full Ruff, Black, isort and backend mypy gates, production image build and the
no-network container smoke check pass. Alembic reports no new upgrade operations,
with an existing warning about the department/worker foreign-key cycle. The
dry-run transaction leaves zero fixture organizations, jobs or messages. No live
provider call was made. The
existing default-secret security test conflicts with Compose's test secret
override; the isolated Docker regression command used was
`docker compose run --rm --no-deps test env -u SECRET_KEY python -m pytest -q --no-cov`.
This removes the override only inside the test process, not from the API.

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
