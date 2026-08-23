"""FastAPI application factory and configuration."""

from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.errors import APIException
from app.api.routes import organizations_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="WorkPulse API",
        description="Workforce communication automation platform",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure with environment variable in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handler for APIException
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions with standard error envelope."""
        request_id = f"req_{uuid4().hex[:16]}"
        error_detail = {
            "code": exc.error_code,
            "message": exc.message,
        }
        if exc.details:
            error_detail["details"] = exc.details

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error": error_detail,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id,
            },
        )

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": __version__}

    # Include routers
    app.include_router(organizations_router)

    return app


app = create_app()
