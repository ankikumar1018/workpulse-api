# Testing Best Practices

## Contents

- [Running Pytest](#running-pytest)
- [Database Access & Test Isolation](#database-access--test-isolation)
- [Test Structure](#test-structure)
- [Test Approach](#test-approach)
- [Behavioral Validation](#behavioral-validation)
- [Admin Maintenance Coverage](#admin-maintenance-coverage)
- [Soft-delete Coverage](#soft-delete-coverage)
- [Imports](#imports)
- [Assertions](#assertions)
- [Parametrize](#parametrize)
- [Pytest Mocking](#pytest-mocking)
- [Spy vs Patch](#spy-vs-patch)
- [Mock Scoping](#mock-scoping)
- [Test Factories](#test-factories)
- [Fixture Selection](#fixture-selection)
- [Test the New Code Path, Not the Fallback](#test-the-new-code-path-not-the-fallback)
- [No `__init__.py` in Test Directories](#no-__init__py-in-test-directories)
- [Review-Comment Severity Taxonomy](#review-comment-severity-taxonomy)

## Running Pytest

Run tests from the backend repository root with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest <path/to/test_file.py> -v
```

Run the complete suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

When the API and database are running in Docker, run tests inside the API
container:

```bash
docker compose exec -T api pytest <path/to/test_file.py> -v
```

Run the quality checks used by this repository:

```bash
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check app tests
.\.venv\Scripts\python.exe -m isort --check app tests
.\.venv\Scripts\python.exe -m mypy app
```

## Database Access & Test Isolation

- Tests that access SQLAlchemy sessions or PostgreSQL must use an explicit
  database fixture and must not depend on data created by another test.
- Prefer an isolated test database or transaction fixture. Roll back changes
  after each test so tests can run in any order.
- Use `transaction=True`-style isolation only when the code under test manages
  its own transaction boundaries.
- Keep pure unit tests independent of PostgreSQL. Use in-memory factory data
  when persistence is not part of the behavior being tested.
- Never use production credentials or call a shared non-test database.
- Tests must remain deterministic when run in parallel or in a random order.

## Test Structure

- Follow Arrange-Act-Assert for every test.
- Prefer existing fixtures and factories over manually assembled objects.
- Test actual functionality rather than only verifying mocked return values.
- Keep tests self-documenting through clear names and focused setup.
- Do not add implementation classes or verbose explanatory docstrings to test
  files when the test name and code already explain the behavior.
- Clear FastAPI dependency overrides after each test that uses them.

```python
async def test_get_organization_returns_expected_data(repository):
    organization = make_organization()
    await repository.create(organization)

    result = await repository.get_by_id(organization.id)

    assert result.id == organization.id
    assert result.name == organization.name
```

## Test Approach

- Prefer unit tests for pure functions, schemas, domain rules, controllers,
  and repository behavior that can run without HTTP middleware.
- Use `TestClient` for focused synchronous API contract tests.
- Use `httpx.AsyncClient` with `ASGITransport` only when the test itself needs
  asynchronous HTTP behavior.
- Use integration tests for database transactions, migrations, dependency
  wiring, and complete request-to-persistence behavior.
- Test response structure, validation, authorization, error behavior, and
  security-sensitive field absence, not private implementation details.
- Mock external providers and expensive side effects. Never call real
  messaging, cloud, or third-party services from tests.

## Behavioral Validation

- Run real code paths. `py_compile`, import checks, and lint only catch syntax,
  import, or style problems.
- For behavior changes, run a focused pytest test and then the complete suite.
- Test the class or function that owns the changed behavior. Do not only test a
  nearby helper or a wrapper that could bypass the new logic.
- Compile-only validation is not sufficient for changes to repositories,
  authorization, caching, background jobs, or provider integrations.

## Admin Maintenance Coverage

When administrative maintenance or reporting actions exist, cover their full
lifecycle:

- preview
- start or dispatch
- status or polling
- download or result retrieval
- delete-all or cleanup
- controlled error responses

Mock database, cache, object storage, queue, and provider failures and assert
that the API returns a controlled response instead of exposing a raw 500 error.

## Soft-delete Coverage

When records are hidden instead of physically deleted, cover:

- name reuse after deletion
- create and update validation
- restore behavior
- delete behavior
- list and read behavior for hidden records

Make the deleted state explicit in test data so uniqueness behavior is not
accidentally tied to all rows.

## Imports

- Import the module under test and patch names through that module. This follows
  the patch-where-used principle.
- Do not add aliases unless they avoid a collision or preserve important
  context.
- Keep imports at module scope unless a verified import cycle requires a local
  import.
- Do not import helpers from another test module. Shared helpers belong in
  `tests/conftest.py`, `tests/factories.py`, or a clearly named shared module.

## Assertions

- Keep all assertions inside the test function body.
- Use assertions that express the exact contract being checked.
- For exceptions, use `pytest.raises` with `match=` whenever the message is
  part of the contract.

```python
with pytest.raises(ValueError, match="organization slug is required"):
    create_organization(name="Acme", slug="")
```

- For mocks, prefer specific assertions:

| Goal | Idiom |
|---|---|
| Exactly one call with arguments | `mock.assert_called_once_with(...)` |
| Last call had arguments | `mock.assert_called_with(...)` |
| Called at least once with arguments | `mock.assert_any_call(...)` |
| Never called | `mock.assert_not_called()` |
| Call count only | `mock.call_count` when specific forms do not fit |

## Parametrize

- Every `@pytest.mark.parametrize` call must provide explicit `ids`.
- Prefer immutable parameter values. Do not mutate lists or dictionaries passed
  as parameter values.
- Use `pytest.param(..., id="...")` when a case needs a distinct readable name
  or a per-case mark.

```python
@pytest.mark.parametrize(
    "status, expected",
    [
        ("active", True),
        ("archived", False),
    ],
    ids=["active-is-visible", "archived-is-hidden"],
)
def test_visibility(status, expected):
    assert is_visible(status) is expected
```

## Pytest Mocking

- Use the repository's pytest mocking fixture or `monkeypatch`; do not use
  `unittest`, `unittest.mock`, or `TestCase` patterns.
- Patch the name where the code under test uses it, not where it was originally
  defined.
- Use `autospec=True` for non-trivial function or method signatures when using
  a mocking plugin.
- Use `MagicMock` only when the code under test calls dunder methods such as
  `__iter__` or `__len__`.
- Prefer real factories and fixtures for domain objects. Mocks are for external
  collaborators, expensive side effects, or behavior that cannot be represented
  by a real test object.

## Spy vs Patch

- Use a spy when the real behavior should run and you only need to inspect
  calls.
- Use a patch when the collaborator must be replaced, such as a database write
  or external provider call.
- Name spy variables with a `_spy` suffix. Patch variables do not use `_spy`.

## Mock Scoping

- Define single-use mocks inside the test that needs them.
- Create a fixture only for mocks shared by multiple tests.
- Keep mock scope as narrow as possible so state cannot leak between tests.

## Test Factories

- Reuse existing deterministic factories from `tests/factories.py` wherever
  possible.
- Add new factories to `tests/factories.py`, not to individual test modules.
- Use `.build()` or an equivalent in-memory factory operation when persistence
  is not required.
- Persist factory results only when the behavior under test reads from the
  database.
- Pass meaningful overrides explicitly instead of hiding behavior in large
  global fixtures.
- Factory defaults should be valid and stable, while each test should override
  only values relevant to its scenario.

## Fixture Selection

- Use fixtures already provided by `tests/conftest.py` and nested test
  configuration files; do not redefine them locally.
- Keep fixtures focused on setup and cleanup. Put scenario-specific values in
  the test body or a factory override.
- Avoid injecting fixtures that are not used by the test.
- Dependency overrides, temporary files, and external-service substitutes must
  be restored after each test.

## Test the New Code Path, Not the Fallback

When a change adds a new branch, the test must steer execution into that
branch. A test that supplies legacy-shaped data can pass while never exercising
the new behavior.

Sanity check: temporarily revert the production change and rerun the test. If it
still passes, the test is probably testing the wrong branch.

```python
@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"stateRequired": False}, True),
        ({"stateRequired": True}, False),
    ],
    ids=["state-optional", "state-required"],
)
def test_state_requirement(payload, expected):
    assert validate_state(payload, state=None) is expected
```

## No `__init__.py` in Test Directories

Do not add `__init__.py` files under `tests/` just to import helpers from
another test module. Pytest discovers test files without them. Shared helpers
belong in `tests/conftest.py`, `tests/factories.py`, or a dedicated shared
helper module.

## Review-Comment Severity Taxonomy

| Label | Meaning | Action |
|---|---|---|
| `[required]` | Project-rule violation; must be fixed before merge. | Fix unconditionally. |
| `[suggestion]` | Cleaner pattern or consistency improvement. | Fix unless there is a concrete reason not to. |
| `[info]` | Teaching or contextual information. | No action expected. |
| `[Question]` | Reviewer requests clarification. | Reply on the review; code change is optional. |
