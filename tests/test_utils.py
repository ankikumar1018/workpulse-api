"""Tests for API utility functions."""

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel

from app.api.utils import camelize


class State(StrEnum):
    """Example response enum."""

    READY = "ready"


class NestedModel(BaseModel):
    """Example nested response model."""

    created_at: str
    alreadyCamel: str


@dataclass
class NestedDataclass:
    """Example nested response dataclass."""

    request_id: str


def test_camelize_nested_response_values():
    """Camelize nested response structures without changing scalar values."""
    value = {
        "request_id": "req-1",
        "nested_data": NestedModel(created_at="now", alreadyCamel="kept"),
        "items": [{"subscription_status": State.READY}],
        "metadata": NestedDataclass(request_id="req-2"),
        "coordinates": (1, 2),
        "tags": {"one", "two"},
        1: "non-string key",
    }

    result = camelize(value)

    assert result["requestId"] == "req-1"
    assert result["nestedData"] == {
        "createdAt": "now",
        "alreadyCamel": "kept",
    }
    assert result["items"] == [{"subscriptionStatus": "ready"}]
    assert result["metadata"] == {"requestId": "req-2"}
    assert result["coordinates"] == [1, 2]
    assert set(result["tags"]) == {"one", "two"}
    assert result[1] == "non-string key"


def test_camelize_key_conversion_edge_cases():
    """Handle empty, snake_case, uppercase, and already-camel keys."""
    value = {
        "": 1,
        "api_url": 2,
        "API_URL": 3,
        "user_name": 4,
        "alreadyCamel": 4,
    }

    assert camelize(value) == {
        "": 1,
        "apiUrl": 2,
        "API_URL": 3,
        "userName": 4,
        "alreadyCamel": 4,
    }


def test_camelize_options():
    """Support string conversion and ignored fields."""
    assert camelize("request_id", transfer_string=True) == "requestId"
    assert camelize(
        {"request_id": "req-1", "nested_data": {"created_at": "now"}},
        ignore_fields={"request_id"},
    ) == {
        "requestId": "req-1",
        "nestedData": {"createdAt": "now"},
    }


