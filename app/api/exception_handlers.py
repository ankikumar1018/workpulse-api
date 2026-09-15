"""Exception handlers registered on the FastAPI app.

Kept separate from app/main.py so the application factory stays focused on
wiring, not error-response formatting.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import APIException
from app.api.utils import camelize, generate_request_id
from app.schemas import ErrorEnvelope
from app.schemas.common import APIError, ResponseStatus


async def api_exception_handler(_request: Request, exc: APIException) -> JSONResponse:
    """Handle custom API exceptions with the standard error envelope."""
    error_detail = APIError(
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    response = ErrorEnvelope(
        status=ResponseStatus.ERROR,
        error=error_detail,
        timestamp=datetime.now(UTC),
        request_id=generate_request_id(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=jsonable_encoder(camelize(response)),
    )


async def request_validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return validation details without exposing internal exception data."""
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "issue": error["msg"],
        }
        for error in exc.errors()
    ]
    response = ErrorEnvelope(
        status=ResponseStatus.ERROR,
        error=APIError(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
        ),
        timestamp=datetime.now(UTC),
        request_id=generate_request_id(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(camelize(response)),
    )


async def unexpected_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Return a stable error without exposing internal exception details."""
    response = ErrorEnvelope(
        status=ResponseStatus.ERROR,
        error=APIError(
            code="INTERNAL_SERVER_ERROR",
            message="Internal server error",
        ),
        timestamp=datetime.now(UTC),
        request_id=generate_request_id(),
    )
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(camelize(response)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every custom exception handler to the given FastAPI app."""
    app.exception_handler(APIException)(api_exception_handler)
    app.exception_handler(RequestValidationError)(request_validation_exception_handler)
    app.exception_handler(Exception)(unexpected_exception_handler)


__all__ = ["register_exception_handlers"]
