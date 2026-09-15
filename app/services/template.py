"""Message template business logic."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.domain.enums import AuditAction, Channel, EntityStatus
from app.domain.template import InvalidTemplateError, TemplateDefinition, TemplateRenderContext
from app.infrastructure.db.models import Project, Template
from app.repositories.audit import AuditRepository
from app.repositories.template import TemplateRepository


class TemplateService:
    """Manage tenant-scoped templates and their activation lifecycle."""

    def __init__(
        self,
        repository: TemplateRepository,
        audit_repository: AuditRepository | None = None,
    ):
        self.repository = repository
        self.audit_repository = audit_repository

    async def _get_project(self, *, project_id: UUID, organization_id: UUID) -> Project:
        project = await self.repository.session.get(Project, project_id)
        if project is None or project.organization_id != organization_id:
            raise NotFoundError(f"Project '{project_id}' not found")
        return project

    @staticmethod
    def _validate_definition(*, organization_id: UUID, name: str, body: str, variable_schema: dict[str, str]) -> None:
        try:
            TemplateDefinition(organization_id, name, body, variable_schema)
        except InvalidTemplateError as exc:
            raise UnprocessableEntityError(str(exc)) from exc

    async def create_template(
        self,
        *,
        organization_id: UUID,
        project_id: UUID,
        actor_user_id: UUID,
        name: str,
        channel: Channel,
        body: str,
        variable_schema: dict[str, str],
        provider_template_name: str | None = None,
        provider_template_language: str | None = None,
    ) -> Template:
        project = await self._get_project(project_id=project_id, organization_id=organization_id)
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot contain new templates")
        self._validate_definition(
            organization_id=organization_id,
            name=name,
            body=body,
            variable_schema=variable_schema,
        )
        if await self.repository.find_by_name(project_id=project_id, name=name, channel=channel):
            raise ConflictError("A template with this name and channel already exists")
        if bool(provider_template_name) != bool(provider_template_language):
            raise UnprocessableEntityError(
                "Provider template name and language must be configured together"
            )
        template = await self.repository.create(
            {
                "organization_id": organization_id,
                "project_id": project_id,
                "name": name,
                "channel": channel,
                "body": body,
                "variable_schema_json": variable_schema,
                "provider_template_name": provider_template_name,
                "provider_template_language": provider_template_language,
            }
        )
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.CREATE,
            template=template,
            metadata={"name": name, "project_id": str(project_id)},
        )
        return template

    async def list_templates(
        self,
        *,
        project_id: UUID,
        organization_id: UUID,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> tuple[list[Template], int]:
        await self._get_project(project_id=project_id, organization_id=organization_id)
        return await self.repository.list_in_project(
            project_id=project_id,
            organization_id=organization_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    async def get_template(self, *, template_id: UUID, organization_id: UUID) -> Template:
        template = await self.repository.get_in_organization(
            template_id=template_id,
            organization_id=organization_id,
        )
        if template is None:
            raise NotFoundError(f"Template '{template_id}' not found")
        return template

    async def render_template(
        self,
        *,
        template_id: UUID,
        organization_id: UUID,
        context: TemplateRenderContext,
    ) -> str:
        """Render an active template against current project and work-item state."""
        template = await self.get_template(template_id=template_id, organization_id=organization_id)
        if template.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived templates cannot be rendered")
        try:
            definition = TemplateDefinition(
                organization_id=template.organization_id,
                name=template.name,
                body=template.body,
                variable_schema=template.variable_schema_json or {},
            )
            return definition.render_context(context)
        except InvalidTemplateError as exc:
            raise UnprocessableEntityError(str(exc)) from exc

    async def update_template(
        self,
        *,
        template_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
        update_data: dict[str, Any],
    ) -> Template:
        template = await self.get_template(template_id=template_id, organization_id=organization_id)
        if template.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived templates cannot be modified")
        project = await self._get_project(
            project_id=template.project_id,
            organization_id=organization_id,
        )
        if project.status == EntityStatus.ARCHIVED:
            raise UnprocessableEntityError("Archived projects cannot contain active templates")
        name = update_data.get("name", template.name)
        channel = update_data.get("channel", template.channel)
        if (name, channel) != (template.name, template.channel) and await self.repository.find_by_name(
            project_id=template.project_id,
            name=name,
            channel=channel,
        ):
            raise ConflictError("A template with this name and channel already exists")
        provider_template_name = update_data.get(
            "provider_template_name", template.provider_template_name
        )
        provider_template_language = update_data.get(
            "provider_template_language", template.provider_template_language
        )
        if bool(provider_template_name) != bool(provider_template_language):
            raise UnprocessableEntityError(
                "Provider template name and language must be configured together"
            )
        self._validate_definition(
            organization_id=organization_id,
            name=name,
            body=update_data.get("body", template.body),
            variable_schema=update_data.get("variable_schema_json", template.variable_schema_json or {}),
        )
        updated = await self.repository.update(template_id, update_data)
        if updated is None:
            raise NotFoundError(f"Template '{template_id}' not found")
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            template=updated,
            metadata=dict(update_data),
        )
        return updated

    async def archive_template(
        self,
        *,
        template_id: UUID,
        organization_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        template = await self.get_template(template_id=template_id, organization_id=organization_id)
        if template.status == EntityStatus.ARCHIVED:
            return
        template.status = EntityStatus.ARCHIVED
        await self.repository.session.commit()
        await self.repository.session.refresh(template)
        await self._audit(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=AuditAction.UPDATE,
            template=template,
            metadata={"status": EntityStatus.ARCHIVED.value},
        )

    async def _audit(
        self,
        *,
        organization_id: UUID,
        actor_user_id: UUID,
        action: AuditAction,
        template: Template,
        metadata: dict[str, Any],
    ) -> None:
        if self.audit_repository is not None:
            await self.audit_repository.record(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=action,
                resource_type="template",
                resource_id=template.id,
                metadata=metadata,
            )


__all__ = ["TemplateService"]
