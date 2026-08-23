"""API error handling and exceptions."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel


class APIError(BaseModel):
    """Machine-readable API error."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class APIException(HTTPException):
    """Base application exception that maps to HTTP responses."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(status_code=status_code)
        self.error_code = error_code
        self.message = message
        self.details = details


class ValidationError(APIException):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: list[dict[str, Any]] | None = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            message=message,
            details=details,
        )


class UnauthorizedError(APIException):
    """Raised when authentication is missing or invalid."""

    def __init__(self, message: str = "Invalid or missing authentication"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message=message,
        )


class ForbiddenError(APIException):
    """Raised when user lacks permission."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message=message,
        )


class NotFoundError(APIException):
    """Raised when resource does not exist."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            message=message,
        )


class ConflictError(APIException):
    """Raised when resource already exists or constraint violated."""

    def __init__(self, message: str = "Conflict"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            message=message,
        )


class UnprocessableEntityError(APIException):
    """Raised when business rule is violated."""

    def __init__(self, message: str = "Cannot process request"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="UNPROCESSABLE_ENTITY",
            message=message,
        )


class RateLimitError(APIException):
    """Raised when rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
        )


class InternalServerError(APIException):
    """Raised for unexpected server errors."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_SERVER_ERROR",
            message=message,
        )


__all__ = [
    "APIError",
    "APIException",
    "ConflictError",
    "ForbiddenError",
    "InternalServerError",
    "NotFoundError",
    "RateLimitError",
    "UnauthorizedError",
    "UnprocessableEntityError",
    "ValidationError",
]
