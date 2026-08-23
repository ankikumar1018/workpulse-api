"""Request schemas."""

from app.schemas.requests.auth import (
    RefreshTokenRequest,
    UserCreateRequest,
    UserRole,
    UserStatus,
    UserUpdateRequest,
)
from app.schemas.requests.department import (
    DepartmentCreateRequest,
    DepartmentStatus,
    DepartmentUpdateRequest,
)
from app.schemas.requests.organization import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
)
from app.schemas.requests.project import ProjectCreateRequest, ProjectStatus, ProjectUpdateRequest
from app.schemas.requests.worker import (
    ContactChannel,
    WorkerConsentStatus,
    WorkerCreateRequest,
    WorkerStatus,
    WorkerUpdateRequest,
)

__all__ = [
    "ContactChannel",
    "DepartmentCreateRequest",
    "DepartmentStatus",
    "DepartmentUpdateRequest",
    "OrganizationCreateRequest",
    "OrganizationUpdateRequest",
    "ProjectCreateRequest",
    "ProjectStatus",
    "ProjectUpdateRequest",
    "RefreshTokenRequest",
    "UserCreateRequest",
    "UserRole",
    "UserStatus",
    "UserUpdateRequest",
    "WorkerConsentStatus",
    "WorkerCreateRequest",
    "WorkerStatus",
    "WorkerUpdateRequest",
]
