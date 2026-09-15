"""Re-exports auth context and controller dependencies as one import surface."""

from app.api.dependencies.auth import AuthContext, CurrentUser, get_auth_context, oauth2_scheme
from app.api.dependencies.controllers import (
    AuthCtrl,
    DepartmentCtrl,
    OrganizationCtrl,
    ProjectCtrl,
    WorkerCtrl,
    WorkItemCtrl,
    get_auth_controller,
    get_department_controller,
    get_organization_controller,
    get_project_controller,
    get_work_item_controller,
    get_worker_controller,
)

__all__ = [
    "AuthContext",
    "AuthCtrl",
    "CurrentUser",
    "DepartmentCtrl",
    "OrganizationCtrl",
    "ProjectCtrl",
    "WorkItemCtrl",
    "WorkerCtrl",
    "get_auth_context",
    "get_auth_controller",
    "get_department_controller",
    "get_organization_controller",
    "get_project_controller",
    "get_work_item_controller",
    "get_worker_controller",
    "oauth2_scheme",
]
