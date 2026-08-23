"""API utilities and common patterns."""

from __future__ import annotations

import re
import uuid
from collections import OrderedDict
from collections.abc import Iterable, Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel

from app.schemas.common import (
    ListEnvelope,
    PaginationMetadata,
    ResponseStatus,
    SuccessEnvelope,
)

camelize_re = re.compile(r"[a-z0-9]?_[a-z0-9]")


def underscore_to_camel(match: re.Match[str]) -> str:
    """Convert one underscore-delimited match to camelCase."""
    group = match.group()
    if len(group) == 3:
        return group[0] + group[2].upper()
    return group[1].upper()


def _camelize_string(value: str) -> str:
    return re.sub(camelize_re, underscore_to_camel, value)


def camelize(value: Any, **options: Any) -> Any:
    """Recursively convert response data and mapping keys to camelCase.

    ``transfer_string=True`` converts a string itself. ``ignore_fields`` skips
    conversion and recursion for matching mapping keys. Supported values include
    Pydantic models, dataclasses, mappings, iterables, enums, and scalars.
    """
    if options.get("transfer_string", False):
        return _camelize_string(value) if isinstance(value, str) else value

    ignore_fields = options.get("ignore_fields") or ()
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python", by_alias=False)
    if isinstance(value, Mapping):
        new_value: dict[Any, Any] = OrderedDict()
        for key, item in value.items():
            new_key = _camelize_string(key) if isinstance(key, str) else key
            if key in ignore_fields or new_key in ignore_fields:
                new_value[new_key] = item
            else:
                new_value[new_key] = camelize(item, **options)
        return new_value
    if is_dataclass(value) and not isinstance(value, type):
        return camelize(
            {field.name: getattr(value, field.name) for field in fields(value)},
            **options,
        )
    if isinstance(value, Enum):
        return camelize(value.value, **options)
    if isinstance(value, Iterable) and not isinstance(value, str | bytes | bytearray):
        return [camelize(item, **options) for item in value]
    return value


def make_success_response(data: Any) -> dict[str, Any]:
    """Build a success response envelope."""
    return cast(dict[str, Any], camelize(SuccessEnvelope(
        status=ResponseStatus.SUCCESS,
        data=data,
        timestamp=datetime.now(UTC),
    )))


def make_list_response(
    data: list[Any],
    total: int,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Build a list response with pagination."""
    has_more = (offset + limit) < total
    return cast(dict[str, Any], camelize(ListEnvelope(
        status=ResponseStatus.SUCCESS,
        data=data,
        pagination=PaginationMetadata(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
        ),
        timestamp=datetime.now(UTC),
    )))


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
    "camelize",
    "generate_request_id",
    "make_list_response",
    "make_success_response",
    "parse_pagination_params",
]
