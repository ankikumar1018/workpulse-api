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
from app.schemas.requests.organization import OrganizationCreateRequest, OrganizationUpdateRequest
from app.schemas.requests.project import ProjectCreateRequest, ProjectStatus, ProjectUpdateRequest
from app.schemas.requests.template import (
    TemplateChannel,
    TemplateCreateRequest,
    TemplateUpdateRequest,
)
from app.schemas.requests.work_item import (
    WorkItemCreateRequest,
    WorkItemUpdateRequest,
    WorkItemUpdateStatusRequest,
    WorkPriority,
    WorkStatus,
)
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
    "TemplateChannel",
    "TemplateCreateRequest",
    "TemplateUpdateRequest",
    "UserCreateRequest",
    "UserRole",
    "UserStatus",
    "UserUpdateRequest",
    "WorkItemCreateRequest",
    "WorkItemUpdateRequest",
    "WorkItemUpdateStatusRequest",
    "WorkPriority",
    "WorkStatus",
    "WorkerConsentStatus",
    "WorkerCreateRequest",
    "WorkerStatus",
    "WorkerUpdateRequest",
]
