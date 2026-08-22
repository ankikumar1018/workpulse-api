"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Create a test database session."""
    # Use in-memory SQLite for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables (will implement Base metadata when domain models are created)
    async with engine.begin():
        # await conn.run_sync(Base.metadata.create_all)
        pass

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for pytest-asyncio."""
    return "asyncio"
