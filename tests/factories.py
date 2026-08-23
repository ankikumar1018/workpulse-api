"""Deterministic factories for reusable test data."""

from datetime import UTC, datetime
from typing import Any

from app.schemas.common import APIError, ErrorEnvelope, PaginationMetadata, ResponseStatus

DEFAULT_TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)


def make_pagination_metadata(
    *,
    total: int = 1,
    limit: int = 20,
    offset: int = 0,
    has_more: bool = False,
) -> PaginationMetadata:
    """Build pagination metadata with deterministic defaults."""
    return PaginationMetadata(
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


def make_error_envelope(
    *,
    code: str = "INVALID",
    message: str = "Invalid request",
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = "req-test",
) -> ErrorEnvelope:
    """Build an error envelope with deterministic defaults."""
    return ErrorEnvelope(
        status=ResponseStatus.ERROR,
        error=APIError(code=code, message=message, details=details),
        timestamp=DEFAULT_TIMESTAMP,
        request_id=request_id,
    )
