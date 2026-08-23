"""API endpoints, request/response schemas and dependencies."""

from app.api.dependencies import AuthContext, CurrentUser, get_auth_context
from app.api.errors import (
    APIException,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableEntityError,
    ValidationError,
)
from app.api.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)

__all__ = [
    "APIException",
    "AuthContext",
    "ConflictError",
    "CurrentUser",
    "ForbiddenError",
    "NotFoundError",
    "OrganizationCreateRequest",
    "OrganizationResponse",
    "OrganizationUpdateRequest",
    "ProjectCreateRequest",
    "ProjectResponse",
    "ProjectUpdateRequest",
    "UnauthorizedError",
    "UnprocessableEntityError",
    "ValidationError",
    "get_auth_context",
]

