"""Provider-agnostic message template rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from uuid import UUID

_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


class InvalidTemplateError(ValueError):
    """Raised when a template contains an invalid or uncontrolled placeholder."""


@dataclass(frozen=True)
class TemplateRenderContext:
    """Current project and work-item state exposed to template rendering."""

    project_name: str
    department_name: str
    current_date: date
    work_status: str
    primary_contact_name: str | None = None
    work_item_title: str | None = None
    priority: str | None = None
    due_date: date | None = None

    def values(self) -> dict[str, object]:
        """Return only values that are available for deterministic rendering."""
        values: dict[str, object] = {
            "project_name": self.project_name,
            "department_name": self.department_name,
            "date": self.current_date.isoformat(),
            "work_status": self.work_status,
        }
        optional_values = {
            "primary_contact_name": self.primary_contact_name,
            "work_item_title": self.work_item_title,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
        }
        values.update({name: value for name, value in optional_values.items() if value is not None})
        return values


@dataclass(frozen=True)
class TemplateDefinition:
    """Validated message template independent of a delivery provider."""

    organization_id: UUID
    name: str
    body: str
    variable_schema: dict[str, str]

    def __post_init__(self) -> None:
        placeholders = set(_PLACEHOLDER_PATTERN.findall(self.body))
        if "{{" in self.body or "}}" in self.body:
            rendered_placeholders = _PLACEHOLDER_PATTERN.sub("", self.body)
            if "{{" in rendered_placeholders or "}}" in rendered_placeholders:
                raise InvalidTemplateError("Template contains an invalid placeholder")
        missing = placeholders - self.variable_schema.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise InvalidTemplateError(f"Template uses undeclared variables: {names}")

    @property
    def placeholders(self) -> frozenset[str]:
        """Return the declared variables referenced by the body."""
        return frozenset(_PLACEHOLDER_PATTERN.findall(self.body))

    def render(self, values: dict[str, object]) -> str:
        """Render the template after requiring every declared variable."""
        missing = self.placeholders - values.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise InvalidTemplateError(f"Missing template variables: {names}")
        return _PLACEHOLDER_PATTERN.sub(
            lambda match: str(values[match.group(1)]),
            self.body,
        )

    def render_context(self, context: TemplateRenderContext) -> str:
        """Render against the explicit current project and work-item context."""
        return self.render(context.values())


__all__ = ["InvalidTemplateError", "TemplateDefinition", "TemplateRenderContext"]
