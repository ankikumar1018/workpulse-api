"""FastAPI application factory and configuration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import APIException
from app.api.routes import auth_router, organizations_router, users_router
from app.api.utils import camelize, generate_request_id, make_success_response
from app.schemas import ErrorEnvelope, SuccessEnvelope
from app.schemas.common import APIError, HealthStatus, ResponseStatus
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

    # Exception handler for APIException
    @app.exception_handler(APIException)
    async def api_exception_handler(_request: Request, exc: APIException):
        """Handle custom API exceptions with standard error envelope."""
        error_detail = APIError(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )
        response = ErrorEnvelope(
            status=ResponseStatus.ERROR,
            error=error_detail,
            timestamp=datetime.now(UTC),
            request_id=generate_request_id(),
        )

        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content=jsonable_encoder(camelize(response)),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ):
        """Return validation details without exposing internal exception data."""
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "issue": error["msg"],
            }
            for error in exc.errors()
        ]
        response = ErrorEnvelope(
            status=ResponseStatus.ERROR,
            error=APIError(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=details,
            ),
            timestamp=datetime.now(UTC),
            request_id=generate_request_id(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(camelize(response)),
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(_request: Request, _exc: Exception):
        """Return a stable error without exposing internal exception details."""
        response = ErrorEnvelope(
            status=ResponseStatus.ERROR,
            error=APIError(
                code="INTERNAL_SERVER_ERROR",
                message="Internal server error",
            ),
            timestamp=datetime.now(UTC),
            request_id=generate_request_id(),
        )
        return JSONResponse(
            status_code=500,
            content=jsonable_encoder(camelize(response)),
        )

    # Health check endpoint
    @app.get("/health", response_model=SuccessEnvelope, tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return make_success_response({
            "status": HealthStatus.HEALTHY,
            "version": settings.APP_VERSION,
        })

    # Include routers
    app.include_router(auth_router)
    app.include_router(organizations_router)
    app.include_router(users_router)

    return app


app = create_app()
