"""API utilities and common patterns."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TypeVar

from app.api.schemas import ListEnvelope, PaginationMetadata, SuccessEnvelope

T = TypeVar("T")


def make_success_response[T](data: T) -> SuccessEnvelope:
    """Build a success response envelope."""
    return SuccessEnvelope(
        status="success",
        data=data,
        timestamp=datetime.utcnow(),
    )


def make_list_response[T](
    data: list[T],
    total: int,
    limit: int,
    offset: int,
) -> ListEnvelope:
    """Build a list response with pagination."""
    has_more = (offset + limit) < total
    return ListEnvelope(
        status="success",
        data=data,
        pagination=PaginationMetadata(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        ),
        timestamp=datetime.utcnow(),
    )


def generate_request_id() -> str:
    """Generate a unique request ID for correlation."""
    return f"req_{uuid.uuid4().hex[:16]}"


def parse_pagination_params(
    limit: int | None = None,
    offset: int | None = None,
) -> tuple[int, int]:
    """
    Parse and validate pagination parameters.

    Returns:
        (limit, offset) tuple with applied defaults and constraints.
    """
    limit = limit or 20
    offset = offset or 0

    # Enforce bounds
    limit = max(1, min(limit, 100))  # 1-100 items per page
    offset = max(0, offset)

    return limit, offset


__all__ = [
    "generate_request_id",
    "make_list_response",
    "make_success_response",
    "parse_pagination_params",
]
