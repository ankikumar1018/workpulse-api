# Python Practices

These rules apply to Python code in WorkPulse API. They complement
[Testing Best Practices](testing-practice.md) and follow the project’s layered
FastAPI architecture.

## Contents

- [Supported Python](#supported-python)
- [Project Boundaries](#project-boundaries)
- [Naming](#naming)
- [Types](#types)
- [Imports](#imports)
- [Functions and Classes](#functions-and-classes)
- [Async Code](#async-code)
- [Pydantic Schemas](#pydantic-schemas)
- [SQLAlchemy](#sqlalchemy)
- [Repositories](#repositories)
- [Errors](#errors)
- [Configuration and Secrets](#configuration-and-secrets)
- [Logging](#logging)
- [Security](#security)
- [Formatting and Quality](#formatting-and-quality)
- [Documentation](#documentation)
- [Python Checklist](#python-checklist)

## Supported Python

- Target Python 3.14, matching `.python-version` and `pyproject.toml`.
- Use built-in generic syntax such as `list[str]`, `dict[str, Any]`, and
  `tuple[T, ...]`.
- Use `X | None` for optional values. Do not introduce `Optional[X]` in new
  code.
- Use modern standard-library features when they improve clarity, but do not
  trade readability for novelty.

## Project Boundaries

Keep responsibilities in the established layers:

- `app/api/`: routes, dependencies, transport schemas, and HTTP error mapping.
- `app/application/`: use cases and orchestration.
- `app/domain/`: business rules, entities, value objects, and domain enums.
- `app/infrastructure/`: database sessions, ORM models, and external adapters.
- `app/workers/`: background jobs and webhook processing.
- `core/`: shared configuration, database primitives, and repository behavior.

Do not place business rules in route functions, Pydantic transport schemas, or
SQLAlchemy models. Do not make domain code depend directly on FastAPI,
PostgreSQL, Cloud Tasks, WhatsApp, or other infrastructure providers.

## Naming

- Use `snake_case` for functions, methods, variables, modules, and parameters.
- Use `PascalCase` for classes, Pydantic models, and type aliases.
- Use `UPPER_SNAKE_CASE` only for module constants.
- Use descriptive names. Avoid one-letter names except for conventional
  short-lived indices or type variables.
- Name retrieval methods by intent: `get_by_id` for identity lookups and
  `find_one` or `find_all` for filtered queries.
- Use explicit state names such as `status`, `priority`, and `delivery_status`.
  Avoid vague names such as `flag`, `processed`, or `data` when a domain name is
  available.

## Types

- Add return annotations to public functions and methods.
- Type parameters and meaningful local variables when inference is not clear.
- Use narrow types at boundaries. Prefer a Pydantic model, enum, or typed
  mapping over an unstructured `dict[str, Any]`.
- Keep `Any` at integration boundaries only, and convert external data into a
  typed representation immediately.
- Use `TypeVar`, `Protocol`, or generic classes when they remove real
  duplication. Do not add abstractions only to satisfy a type checker.
- Run mypy against `app` before merging changes.

```python
from collections.abc import Sequence


def active_slugs(slugs: Sequence[str]) -> list[str]:
    return [slug for slug in slugs if slug]
```

## Imports

- Keep imports at module scope unless a verified import cycle requires a local
  import.
- Order standard-library, third-party, and local imports in separate groups.
- Import from the module that owns the public symbol.
- Avoid wildcard imports and unnecessary aliases.
- Remove unused imports rather than suppressing the linter.
- Let isort and Ruff enforce the repository’s import style.

```python
from datetime import UTC, datetime

from fastapi import APIRouter

from app.schemas.common import ResponseStatus
```

## Functions and Classes

- Keep functions focused on one behavior and make dependencies explicit.
- Prefer early returns for invalid or exceptional conditions.
- Avoid hidden mutation of arguments and module-level mutable state.
- Use keyword-only arguments when positional confusion is likely.
- Keep constructors lightweight. Dependency wiring belongs in FastAPI
  dependencies or application composition.
- Use dataclasses or Pydantic models for structured values instead of loosely
  shaped dictionaries.
- Do not catch `Exception` unless the boundary is deliberately converting it
  into a stable application error and logs retain diagnostic context.

## Async Code

- Use `async def` for operations that await database or external I/O.
- Await every coroutine. Do not call blocking database, filesystem, or network
  code directly from an async request path.
- Use SQLAlchemy’s async session APIs consistently with the existing session
  lifecycle.
- Keep CPU-heavy work out of request handlers; move it to a worker or an
  explicitly managed background operation.
- Do not create event loops, sessions, or clients inside individual operations
  when the application lifecycle can own them.
- Close async clients and sessions deterministically through lifespan or
  dependency cleanup.

## Pydantic Schemas

- Use request models for input and response models for output.
- Keep transport validation in `app/schemas/`; keep business invariants in the
  application or domain layer.
- Use explicit field constraints, descriptions, and enums for public values.
- Use the project’s camel-case alias configuration for JSON contracts while
  keeping Python fields in `snake_case`.
- Use `model_dump(exclude_unset=True)` for partial updates so omitted fields are
  not accidentally overwritten.
- Do not expose ORM objects or internal fields directly when a response schema
  can define the public contract.

```python
from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
```

## SQLAlchemy

- Use SQLAlchemy 2.x typed mappings with `Mapped` and `mapped_column`.
- Keep database models in `app/infrastructure/` and domain rules outside ORM
  declarations.
- Make nullability, uniqueness, foreign keys, indexes, and server defaults
  explicit.
- Use transactions with clear ownership. The layer that starts a transaction
  must define its commit and rollback behavior.
- Do not commit from a read-only query.
- Load relationships intentionally; avoid accidental lazy I/O in response
  serialization.
- Every schema change requires a focused, reviewed Alembic migration.

## Repositories

- Repositories own persistence queries, not business policy.
- Use `get_by_id` for primary-key identity retrieval.
- Use `find_one` for one record matching filters and `find_all` for filtered
  collections.
- Return domain or ORM objects consistently within the existing repository
  boundary; do not mix response schemas into repository methods.
- Keep filtering, pagination, and count behavior deterministic.
- Translate database constraint failures into application-level errors at the
  appropriate boundary.

## Errors

- Raise the project’s API exception types for expected failures.
- Use stable error codes and messages from the common response contract.
- Map validation, authentication, authorization, not-found, conflict, and
  internal errors to their intended HTTP status codes.
- Never expose stack traces, SQL, tokens, passwords, or provider credentials in
  API responses.
- Preserve the response envelope and camelized JSON contract for every API
  error.
- Log unexpected failures with context, then return the stable internal-server
  error response.

## Configuration and Secrets

- Read configuration through `core.config.settings`; do not read environment
  variables throughout application code.
- Keep defaults safe for local development and require production secrets to be
  supplied by deployment configuration.
- Never commit `.env` files, credentials, private keys, access tokens, or
  provider secrets.
- Keep security-sensitive settings configurable, including secret keys,
  database connection values, token expiry, and CORS policy.
- Use `cached_property` or application lifespan ownership for derived resources
  that should be initialized once.

## Logging

- Use structured logging for request, job, provider, and database-boundary
  events.
- Include a request or job correlation ID when available.
- Log useful identifiers such as resource IDs and error codes, but avoid
  unnecessary personal data.
- Never log passwords, JWT values, authorization headers, connection strings, or
  secret configuration.
- Log exceptions with enough context to diagnose the failure without requiring
  sensitive payloads.

## Security

- Treat all request data and provider responses as untrusted input.
- Validate JWT signatures, expiry, token type, and required claims before using
  authentication context.
- Enforce authentication and organization scoping at the API/application
  boundary, not only in the frontend.
- Use constant-time password verification through a maintained password-hashing
  library when password authentication is added.
- Store refresh-token hashes rather than raw refresh tokens.
- Keep provider-specific authentication and payload handling inside adapters.
- Do not disable authentication or authorization in production code to simplify
  tests; use explicit FastAPI dependency overrides in tests.

## Formatting and Quality

Run the repository quality gates from the backend root:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check app tests
.\.venv\Scripts\python.exe -m isort --check app tests
.\.venv\Scripts\python.exe -m mypy app
.\.venv\Scripts\python.exe -m pytest -q
```

- Keep line length and formatting consistent with `pyproject.toml`.
- Fix Ruff findings instead of adding broad ignores.
- Do not weaken strict pytest settings or warning filters to make a test pass.
- Keep comments short and explain only non-obvious decisions.
- Prefer code that is clear without comments over comments that narrate syntax.

## Documentation

- Add docstrings to public modules, classes, and non-obvious public functions.
- Docstrings should explain purpose, constraints, or side effects; do not repeat
  the function name or every obvious parameter assignment.
- Update API and development documentation when a public behavior or workflow
  changes.
- Keep examples executable or clearly marked as illustrative.
- Link to canonical project documentation instead of duplicating large sections.

## Python Checklist

Before opening a pull request, confirm:

- The code follows the layer boundaries.
- Public functions and meaningful values have appropriate types.
- Async I/O is awaited and resources have deterministic lifecycles.
- Request and response contracts use the shared Pydantic conventions.
- Repository retrieval names follow `get_*` and `find_*` semantics.
- Expected failures use the common API error contract.
- Secrets and sensitive payloads are not logged or committed.
- Ruff, Black, isort, mypy, and the relevant pytest suite pass.
- A behavior-focused test covers every new or changed code path.
