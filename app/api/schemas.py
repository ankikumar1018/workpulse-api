"""Pydantic schemas for API request/response validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ValidationErrorDetail(BaseModel):
    """Field-level validation error detail."""

    field: str = Field(description="Field name that failed validation")
    issue: str = Field(description="Human-readable error message")


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""

    status: str = Field(default="error", description="Always 'error'")
    error: dict[str, Any] = Field(description="Error details")
    timestamp: datetime = Field(description="UTC timestamp of error")
    request_id: str | None = Field(None, description="Request correlation ID")

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "error",
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid input",
            "details": [
                {"field": "name", "issue": "Field required"}
            ]
        },
        "timestamp": "2026-08-23T14:22:30.123456Z",
        "request_id": "req_abc123def456"
    }})


class PaginationMetadata(BaseModel):
    """Pagination information for list responses."""

    total: int = Field(description="Total count of items")
    limit: int = Field(description="Items per page")
    offset: int = Field(description="Items skipped from start")
    has_more: bool = Field(description="Whether more items exist")

    model_config = ConfigDict(json_schema_extra={"example": {
        "total": 150,
        "limit": 20,
        "offset": 0,
        "has_more": True
    }})


class SuccessEnvelope[T](BaseModel):
    """Standard success response envelope (single item)."""

    status: str = Field(default="success", description="Always 'success'")
    data: Any = Field(description="Response payload")
    timestamp: datetime = Field(description="UTC timestamp")


class ListEnvelope[T](BaseModel):
    """Standard success response envelope (list)."""

    status: str = Field(default="success", description="Always 'success'")
    data: list[Any] = Field(description="Array of items")
    pagination: PaginationMetadata = Field(description="Pagination metadata")
    timestamp: datetime = Field(description="UTC timestamp")


# ============================================================================
# Organization Schemas
# ============================================================================

class OrganizationCreateRequest(BaseModel):
    """Create organization request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization display name"
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="URL-safe unique slug"
    )

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Acme Interior Design",
        "slug": "acme-corp"
    }})


class OrganizationUpdateRequest(BaseModel):
    """Update organization request (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(None, description="'provisioning', 'active', 'inactive', 'suspended', 'archived'")
    subscription_status: str | None = Field(None, description="'trialing', 'active', 'past_due', 'canceled', 'expired'")

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "active"
    }})


class OrganizationResponse(BaseModel):
    """Organization response."""

    id: UUID
    name: str
    slug: str
    status: str
    subscription_status: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Acme Corp",
        "slug": "acme-corp",
        "status": "active",
        "subscription_status": "active",
        "created_at": "2026-01-15T10:30:00Z",
        "updated_at": "2026-01-15T10:30:00Z"
    }})


# ============================================================================
# Project Schemas
# ============================================================================

class ProjectCreateRequest(BaseModel):
    """Create project request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Project name"
    )
    description: str | None = Field(None, description="Project description")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Q4 Renovation",
        "description": "Interior refresh project",
        "start_date": "2026-10-01",
        "end_date": "2026-12-31"
    }})


class ProjectUpdateRequest(BaseModel):
    """Update project request (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    status: str | None = Field(None, description="'active' or 'archived'")
    start_date: str | None = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (YYYY-MM-DD)")

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "active"
    }})


class ProjectResponse(BaseModel):
    """Project response."""

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    status: str
    start_date: str | None
    end_date: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "660e8400-e29b-41d4-a716-446655440000",
        "organization_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Q4 Renovation",
        "description": "Interior refresh",
        "status": "active",
        "start_date": "2026-10-01",
        "end_date": "2026-12-31",
        "created_at": "2026-08-01T09:00:00Z",
        "updated_at": "2026-08-01T09:00:00Z"
    }})


# ============================================================================
# Department Schemas
# ============================================================================

class DepartmentCreateRequest(BaseModel):
    """Create department request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Department name"
    )
    description: str | None = Field(None, description="Department description")

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Installation Team",
        "description": "On-site installation and setup"
    }})


class DepartmentUpdateRequest(BaseModel):
    """Update department request (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None)
    status: str | None = Field(None, description="'active' or 'archived'")

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "active"
    }})


class DepartmentResponse(BaseModel):
    """Department response."""

    id: UUID
    project_id: UUID
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "770e8400-e29b-41d4-a716-446655440000",
        "project_id": "660e8400-e29b-41d4-a716-446655440000",
        "name": "Installation Team",
        "description": "On-site installation",
        "status": "active",
        "created_at": "2026-08-01T09:00:00Z",
        "updated_at": "2026-08-01T09:00:00Z"
    }})


# ============================================================================
# Worker Schemas
# ============================================================================

class WorkerCreateRequest(BaseModel):
    """Create worker request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Worker name"
    )
    email: str | None = Field(None, description="Email address")

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "John Smith",
        "email": "john.smith@example.com"
    }})


class WorkerUpdateRequest(BaseModel):
    """Update worker request (partial)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    email: str | None = Field(None)
    status: str | None = Field(None, description="'active' or 'inactive'")

    model_config = ConfigDict(json_schema_extra={"example": {
        "status": "active"
    }})


class WorkerResponse(BaseModel):
    """Worker response."""

    id: UUID
    organization_id: UUID
    name: str
    email: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(json_schema_extra={"example": {
        "id": "880e8400-e29b-41d4-a716-446655440000",
        "organization_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "John Smith",
        "email": "john.smith@example.com",
        "status": "active",
        "created_at": "2026-08-01T09:00:00Z",
        "updated_at": "2026-08-01T09:00:00Z"
    }})


__all__ = [
    "DepartmentCreateRequest",
    "DepartmentResponse",
    "DepartmentUpdateRequest",
    "ErrorEnvelope",
    "ListEnvelope",
    "OrganizationCreateRequest",
    "OrganizationResponse",
    "OrganizationUpdateRequest",
    "PaginationMetadata",
    "ProjectCreateRequest",
    "ProjectResponse",
    "ProjectUpdateRequest",
    "SuccessEnvelope",
    "ValidationErrorDetail",
    "WorkerCreateRequest",
    "WorkerResponse",
    "WorkerUpdateRequest",
]
