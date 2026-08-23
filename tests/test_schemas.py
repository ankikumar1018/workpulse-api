"""Tests for shared API response schemas."""

from tests.factories import make_error_envelope, make_pagination_metadata


def test_common_response_schemas_expose_camel_case_aliases():
    """Serialize common response fields with the public API naming contract."""
    pagination = make_pagination_metadata()
    error = make_error_envelope()

    assert pagination.model_dump(by_alias=True) == {
        "total": 1,
        "limit": 20,
        "offset": 0,
        "hasMore": False,
    }
    assert error.model_dump(by_alias=True)["requestId"] == "req-test"
