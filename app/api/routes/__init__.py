"""API route modules."""

from app.api.routes.auth import router as auth_router
from app.api.routes.departments import router as departments_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.projects import router as projects_router
from app.api.routes.users import router as users_router
from app.api.routes.workers import router as workers_router

__all__ = [
    "auth_router",
    "departments_router",
    "organizations_router",
    "projects_router",
    "users_router",
    "workers_router",
]
