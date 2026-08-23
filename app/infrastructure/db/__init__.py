"""Database models and metadata exports."""

# Import models so metadata is fully populated for Alembic autogenerate.
from app.infrastructure.db import models as _models  # noqa: F401
from app.infrastructure.db.base import Base

__all__ = ["Base"]
