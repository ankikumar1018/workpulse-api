"""Aggregate API router: composes every resource router under one version prefix."""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.departments import router as departments_router
from app.api.routes.organizations import router as organizations_router
from app.api.routes.projects import router as projects_router
from app.api.routes.users import router as users_router
from app.api.routes.work_items import router as work_items_router
from app.api.routes.workers import router as workers_router
from app.api.versioning import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(projects_router)
api_router.include_router(departments_router)
api_router.include_router(workers_router)
api_router.include_router(work_items_router)
api_router.include_router(users_router)

__all__ = ["api_router"]
