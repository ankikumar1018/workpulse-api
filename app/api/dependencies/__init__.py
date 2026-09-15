"""Re-exports auth context and service dependencies as one import surface."""

from app.api.dependencies.auth import AuthContext, CurrentUser, get_auth_context, oauth2_scheme
from app.api.dependencies.services import (
    AuthSvc,
    DepartmentSvc,
    OrganizationSvc,
    ProjectSvc,
    WorkerSvc,
    WorkItemSvc,
    get_auth_service,
    get_department_service,
    get_organization_service,
    get_project_service,
    get_work_item_service,
    get_worker_service,
)

__all__ = [
    "AuthContext",
    "AuthSvc",
    "CurrentUser",
    "DepartmentSvc",
    "OrganizationSvc",
    "ProjectSvc",
    "WorkItemSvc",
    "WorkerSvc",
    "get_auth_context",
    "get_auth_service",
    "get_department_service",
    "get_organization_service",
    "get_project_service",
    "get_work_item_service",
    "get_worker_service",
    "oauth2_scheme",
]
