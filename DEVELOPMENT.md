# Development Setup Guide

This guide walks through setting up the WorkPulse API development environment.

## Prerequisites

- **Python 3.11+** (pinned to 3.11 in `.python-version`)
- **uv** - Fast Python package manager
- **Git** - Version control
- **Docker & Docker Compose** - For PostgreSQL and containerized development
- **PostgreSQL 13+** - For production-like database testing

## Installation Steps

### 1. Install uv (if not already installed)

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Verify uv Installation

```bash
uv --version
# Should output: uv 0.12.x or later
```

### 3. Install Python 3.11 (if needed)

uv will automatically use the pinned version from `.python-version`:
```bash
uv python install 3.11
```

### 4. Create Virtual Environment and Install Dependencies

Navigate to the backend directory:
```bash
cd workpulse-api
```

Create virtual environment and install all dependencies (including dev tools):
```bash
uv sync
```

This will:
- Create `.venv/` virtual environment
- Install all dependencies from `pyproject.toml`
- Lock versions in `uv.lock`
- Install dev dependencies for testing and linting

Verify installation:
```bash
uv run python --version
# Should output: Python 3.11.x
```

### 5. Set Up Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Update `.env` with your local configuration (or leave defaults for local PostgreSQL):
```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/workpulse
PYTHONENV=development
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
```

### 6. Start PostgreSQL (Docker)

Option A: Using docker-compose (recommended):
```bash
docker-compose up -d postgres
```

This starts PostgreSQL in the background with:
- Database: `workpulse`
- User: `postgres`
- Password: `postgres`
- Port: `5432`

Option B: Using local PostgreSQL:
```bash
# Ensure PostgreSQL is running and create database
psql -U postgres -c "CREATE DATABASE workpulse;"
```

### 7. Run Database Migrations

```bash
uv run alembic upgrade head
```

This creates all necessary database tables from migrations.

### 8. Verify Setup

Run health check:
```bash
uv run fastapi dev app/main.py --port 8000
```

Test the API:
```bash
# In another terminal:
curl http://localhost:8000/health
# Should return: {"status":"healthy","version":"0.1.0"}
```

Access API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 9. Run Tests

Run all tests:
```bash
uv run pytest
```

Run with coverage report:
```bash
uv run pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

Run specific test file:
```bash
uv run pytest tests/test_app.py
```

### 10. Code Quality Checks

Run all checks:
```bash
uv run ruff check .
uv run black --check app tests
uv run isort --check app tests
uv run mypy app
```

Auto-fix issues:
```bash
uv run ruff check --fix .
uv run black app tests
uv run isort app tests
```

## Development Workflow

### Starting the Development Server

```bash
# Terminal 1: Start Docker services
docker-compose up -d

# Terminal 2: Start FastAPI development server (with auto-reload)
uv run fastapi dev app/main.py --port 8000
```

### Making Code Changes

The development server auto-reloads when you modify files. The workflow:
1. Edit code in `app/`
2. Server reloads automatically
3. Check `http://localhost:8000/docs` to see your changes

### Adding Dependencies

Install a new package:
```bash
uv add requests
```

Install a dev-only dependency:
```bash
uv add --dev pytest-plugin-name
```

### Creating Database Migrations

After updating domain models:
```bash
# Create auto-generated migration
uv run alembic revision --autogenerate -m "Add users table"

# Review the generated file in alembic/versions/
# Edit if needed

# Apply migration
uv run alembic upgrade head
```

### Debugging

Enable verbose logging:
```bash
RUST_LOG=debug uv run fastapi dev app/main.py
```

Use Python debugger:
```python
# In your code
import pdb; pdb.set_trace()

# Or in VS Code, set breakpoint and run debugger
```

## Docker-Based Development

### Using docker-compose for Full Stack

The `docker-compose.yml` includes:
- **postgres**: PostgreSQL database
- **api**: FastAPI application (auto-reload enabled)
- **pgadmin**: Database admin UI at http://localhost:5050

Start full stack:
```bash
docker-compose up
```

View logs:
```bash
docker-compose logs -f api
```

Stop services:
```bash
docker-compose down
```

### Building Production Image

Build Docker image:
```bash
docker build -t workpulse-api:latest .
```

Run container:
```bash
docker run -e DATABASE_URL=postgresql+psycopg://... -p 8000:8000 workpulse-api:latest
```

## Troubleshooting

### Issue: `uv: command not found`

**Solution**: Add uv to PATH or reinstall:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Restart terminal
```

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Ensure you've synced dependencies:
```bash
uv sync
```

### Issue: Database connection error

**Solution**: Verify PostgreSQL is running:
```bash
# Check Docker containers
docker ps | grep postgres

# Or check local PostgreSQL
psql -U postgres -d workpulse -c "SELECT 1"
```

### Issue: `psycopg` import error

**Solution**: Reinstall with binary support:
```bash
uv add --force psycopg[binary]
```

### Issue: Port 8000 already in use

**Solution**: Use different port:
```bash
uv run fastapi dev app/main.py --port 8001
```

## Best Practices

### Virtual Environment

Always use uv venv:
```bash
# Don't activate venv manually, let uv handle it
uv run <command>  # Automatically uses .venv

# Or activate manually for persistent session
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Commit Hooks (Optional)

Set up pre-commit hooks:
```bash
uv add --dev pre-commit
uv run pre-commit install
```

Hooks will run on every commit to check code quality.

### Testing

Write tests as you develop:
```bash
# Place tests in tests/ directory
# Prefix test files with test_ or suffix with _test.py

uv run pytest --watch  # Auto-run tests on file changes
```

## Next Steps

Once setup is complete:
1. Read [README.md](./README.md) for API documentation
2. Check [../../WorkPulse.html](../../WorkPulse.html) for architecture
3. Start implementing features from Stage 1-2 of the backlog
4. Write tests for each new feature

## Getting Help

- **uv docs**: https://docs.astral.sh/uv/
- **FastAPI docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy docs**: https://docs.sqlalchemy.org/
- **Pydantic docs**: https://docs.pydantic.dev/

## IDE Setup

### VS Code

1. Install extensions:
   - Python (Microsoft)
   - Pylance
   - Ruff
   - Pytest

2. Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ]
}
```

### PyCharm

1. Set interpreter: Settings → Project → Python Interpreter → .venv
2. Enable pytest: Settings → Tools → Python Integrated Tools → Testing → pytest
3. Configure code style: Settings → Editor → Code Style → Python

Enjoy developing! 🚀
