"""Core module - contains boilerplate code."""

from core.config import Settings, settings
from core.database import (
    Base,
    TimestampMixin,
    async_session_maker,
    close_db,
    engine,
    get_session,
    init_db,
)
from core.repository import BaseRepository

# NOTE: Factory is intentionally NOT imported here to avoid circular dependencies
# Import it directly when needed: from core.factory import Factory

__all__ = [
    "Base",
    "BaseRepository",
    "Settings",
    "TimestampMixin",
    "async_session_maker",
    "close_db",
    "engine",
    "get_session",
    "init_db",
    "settings",
]
