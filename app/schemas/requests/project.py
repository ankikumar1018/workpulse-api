"""Project request schemas."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ProjectStatus = Literal["active", "archived"]


class ProjectCreateRequest(BaseModel):
    """Create a project in the authenticated organization."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> ProjectCreateRequest:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ProjectUpdateRequest(BaseModel):
    """Partially update a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> ProjectUpdateRequest:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


__all__ = ["ProjectCreateRequest", "ProjectStatus", "ProjectUpdateRequest"]
