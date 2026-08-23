"""Database session and connection management."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# Build async database URL
def get_database_url() -> str:
    """Build database connection URL from environment."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "workpulse")

    # Use psycopg3 async driver (new style)
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


# Create async engine
engine = create_async_engine(
    get_database_url(),
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    future=True,
    pool_size=20,
    max_overflow=0,
)

# Session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Dependency to get async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


__all__ = [
    "async_session_maker",
    "close_db",
    "engine",
    "get_database_url",
    "get_db_session",
]
