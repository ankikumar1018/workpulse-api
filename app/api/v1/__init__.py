"""Aggregate API router: composes every resource router under one version prefix."""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.departments import router as departments_router
from app.api.v1.endpoints.messages import router as messages_router
from app.api.v1.endpoints.organizations import router as organizations_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.templates import router as templates_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.work_items import router as work_items_router
from app.api.v1.endpoints.workers import router as workers_router
from app.api.v1.endpoints.whatsapp_webhooks import router as whatsapp_webhooks_router
from app.api.versioning import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(messages_router)
api_router.include_router(projects_router)
api_router.include_router(templates_router)
api_router.include_router(departments_router)
api_router.include_router(workers_router)
api_router.include_router(work_items_router)
api_router.include_router(users_router)
api_router.include_router(whatsapp_webhooks_router)

__all__ = ["api_router"]
