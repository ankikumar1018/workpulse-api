# This Dockerfile builds separate images for production and development tasks.
#
# Production should be small and contain only what the API needs at runtime.
# Development/test should include tools such as pytest, ruff, black, isort, and
# mypy without shipping those tools in the production image.

# The production dependency stage creates a locked virtual environment with only
# runtime dependencies from uv.lock.
FROM python:3.14-slim AS production-dependencies

# uv installs dependencies from pyproject.toml and uv.lock. It only lives in the
# dependency-building stages, not in the final production image.
RUN pip install --no-cache-dir uv

# All following paths are relative to /app inside the container.
WORKDIR /app

# README.md is copied because pyproject.toml references it as package metadata.
COPY pyproject.toml uv.lock README.md ./

# --frozen fails the build if uv.lock and pyproject.toml disagree.
# --no-dev keeps test/lint/type-check tools out of the production image.
# --no-install-project avoids installing the local package before source exists;
# the source is copied into /app later and imported from the working directory.
# --compile-bytecode compiles Python files during build for faster startup.
RUN uv sync --frozen --no-dev --no-install-project --compile-bytecode

# The development dependency stage extends the production dependency stage with
# dev tools. The test service uses this target; production does not.
FROM production-dependencies AS development-dependencies

# --group dev adds pytest, ruff, black, isort, mypy, and test helpers.
RUN uv sync --frozen --group dev --no-install-project --compile-bytecode

# Shared runtime base for both production and development images.
FROM python:3.14-slim AS runtime-base

# Keep the application in a predictable location inside the container.
WORKDIR /app

# Put the virtual environment first on PATH so commands resolve without manually
# activating the venv. PYTHONUNBUFFERED sends logs directly to Docker output.
# PYTHONDONTWRITEBYTECODE avoids creating __pycache__ files at runtime.
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy only runtime source and migration files. Tests and dev-only project files
# are intentionally left out of the production image.
COPY app/ app/
COPY core/ core/
COPY alembic/ alembic/
COPY alembic.ini .

# Run as a non-root user to reduce container privileges in production.
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Docker uses this command to decide whether the API container is healthy.
# It uses Python's standard library so the image does not need curl or wget.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"]

# Default command when this image is run directly. docker-compose.yml overrides
# it locally so migrations run before the development server starts.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development/test image. It has dev dependencies and test files, but it is not
# used for the running API service.
FROM runtime-base AS development

COPY --from=development-dependencies --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser tests/ tests/
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./

# Production image. This is intentionally the final target so plain
# `docker build .` produces the production-grade image by default.
FROM runtime-base AS production

COPY --from=production-dependencies --chown=appuser:appuser /app/.venv /app/.venv
