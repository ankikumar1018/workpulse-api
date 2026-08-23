"""Department request schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

DepartmentStatus = Literal["active", "archived"]


class DepartmentCreateRequest(BaseModel):
    """Create a department in a project."""

    name: str = Field(min_length=1, max_length=255)


class DepartmentUpdateRequest(BaseModel):
    """Partially update a department."""

    name: str | None = Field(None, min_length=1, max_length=255)
    primary_contact_worker_id: UUID | None = None
    status: DepartmentStatus | None = None


__all__ = ["DepartmentCreateRequest", "DepartmentStatus", "DepartmentUpdateRequest"]
