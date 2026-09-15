"""FastAPI application factory and configuration."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.utils import make_success_response
from app.api.v1 import api_router
from app.schemas import SuccessEnvelope
from app.schemas.common import HealthStatus
from core.config import settings
from core.database import close_db, init_db


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await init_db()
        yield
        await close_db()

    app = FastAPI(
        title=settings.APP_NAME,
        description="Workforce communication automation platform",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    register_exception_handlers(app)

    # Health check endpoint
    @app.get("/health", response_model=SuccessEnvelope, tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return make_success_response(
            {
                "status": HealthStatus.HEALTHY,
                "version": settings.APP_VERSION,
            }
        )

    app.include_router(api_router)

    return app


app = create_app()
