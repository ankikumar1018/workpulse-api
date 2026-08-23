"""Common/shared schemas used across the application."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    """Convert a delimited field name to camelCase."""
    if not value:
        return value

    parts = [part for part in re.split(r"[_\-\s]+", value) if part]
    if len(parts) == 1:
        return value

    return parts[0].lower() + "".join(
        part[:1].upper() + part[1:].lower() for part in parts[1:]
    )


class ResponseStatus(StrEnum):
    """Status values used by API response envelopes."""

    SUCCESS = "success"
    ERROR = "error"


class HealthStatus(StrEnum):
    """Health states exposed by the health endpoint."""

    HEALTHY = "healthy"


class ValidationErrorDetail(BaseModel):
    """Field-level validation error detail."""

    field: str = Field(description="Field name that failed validation")
    issue: str = Field(description="Human-readable error message")


class APIError(BaseModel):
    """Machine-readable API error."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""

    status: ResponseStatus = Field(default=ResponseStatus.ERROR)
    error: APIError = Field(description="Error details")
    timestamp: datetime = Field(description="UTC timestamp of error")
    request_id: str | None = Field(None, description="Request correlation ID")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={"example": {
            "status": ResponseStatus.ERROR,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input",
                "details": [
                    {"field": "name", "issue": "Field required"},
                ],
            },
            "timestamp": "2026-08-23T14:22:30.123456Z",
            "request_id": "req_abc123def456",
        }},
    )


class PaginationMetadata(BaseModel):
    """Pagination information for list responses."""

    total: int = Field(description="Total count of items")
    limit: int = Field(description="Items per page")
    offset: int = Field(description="Items skipped from start")
    has_more: bool = Field(description="Whether more items exist")

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={"example": {
            "total": 150,
            "limit": 20,
            "offset": 0,
            "has_more": True,
        }},
    )


class SuccessEnvelope(BaseModel):
    """Standard success response envelope (single item)."""

    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    data: Any = Field(description="Response payload")
    timestamp: datetime = Field(description="UTC timestamp")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ListEnvelope(BaseModel):
    """Standard success response envelope (list)."""

    status: ResponseStatus = Field(default=ResponseStatus.SUCCESS)
    data: list[Any] = Field(description="Array of items")
    pagination: PaginationMetadata = Field(description="Pagination metadata")
    timestamp: datetime = Field(description="UTC timestamp")

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


__all__ = [
    "APIError",
    "ErrorEnvelope",
    "HealthStatus",
    "ListEnvelope",
    "PaginationMetadata",
    "ResponseStatus",
    "SuccessEnvelope",
    "ValidationErrorDetail",
    "to_camel",
]
