"""Worker request schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

WorkerStatus = Literal["active", "inactive"]


class WorkerCreateRequest(BaseModel):
    """Create a worker in a department."""

    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(pattern=r"^\+[1-9][0-9]{1,14}$", max_length=16)


class WorkerUpdateRequest(BaseModel):
    """Partially update a worker."""

    department_id: UUID | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    phone_number: str | None = Field(None, pattern=r"^\+[1-9][0-9]{1,14}$", max_length=16)
    status: WorkerStatus | None = None


__all__ = ["WorkerCreateRequest", "WorkerStatus", "WorkerUpdateRequest"]
