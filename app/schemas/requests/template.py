"""Message template request schemas."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

TemplateChannel = Literal["whatsapp"]
_VARIABLE_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class TemplateCreateRequest(BaseModel):
    """Create a project-scoped message template."""

    name: str = Field(min_length=1, max_length=255)
    channel: TemplateChannel = "whatsapp"
    body: str = Field(min_length=1, max_length=10000)
    variable_schema: dict[str, str] = Field(default_factory=dict)
    provider_template_name: str | None = Field(None, min_length=1, max_length=512)
    provider_template_language: str | None = Field(None, min_length=2, max_length=32)

    @field_validator("variable_schema")
    @classmethod
    def validate_variable_names(cls, value: dict[str, str]) -> dict[str, str]:
        invalid = sorted(name for name in value if not _VARIABLE_NAME.fullmatch(name))
        if invalid:
            raise ValueError(f"Invalid template variable name: {invalid[0]}")
        return value


class TemplateUpdateRequest(BaseModel):
    """Partially update an active message template."""

    name: str | None = Field(None, min_length=1, max_length=255)
    channel: TemplateChannel | None = None
    body: str | None = Field(None, min_length=1, max_length=10000)
    variable_schema: dict[str, str] | None = None
    provider_template_name: str | None = Field(None, min_length=1, max_length=512)
    provider_template_language: str | None = Field(None, min_length=2, max_length=32)

    @field_validator("variable_schema")
    @classmethod
    def validate_variable_names(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        invalid = sorted(name for name in value if not _VARIABLE_NAME.fullmatch(name))
        if invalid:
            raise ValueError(f"Invalid template variable name: {invalid[0]}")
        return value


__all__ = ["TemplateChannel", "TemplateCreateRequest", "TemplateUpdateRequest"]
