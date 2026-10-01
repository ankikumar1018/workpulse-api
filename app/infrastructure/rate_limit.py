"""Process-local outbound channel rate limiting."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any


class InMemoryChannelRateLimiter:
    """Throttle outbound dispatches per channel within one application process."""

    def __init__(self, *, rate_per_second: float) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be greater than zero")
        self._interval_seconds = 1 / rate_per_second
        self._next_available: dict[str, float] = defaultdict(float)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, *, channel: Any) -> None:
        """Wait until the next dispatch for the channel is allowed."""
        channel_name = getattr(channel, "value", str(channel))
        async with self._locks[channel_name]:
            now = time.monotonic()
            delay = self._next_available[channel_name] - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._next_available[channel_name] = time.monotonic() + self._interval_seconds


__all__ = ["InMemoryChannelRateLimiter"]
