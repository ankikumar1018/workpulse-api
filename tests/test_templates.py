from datetime import date
from uuid import uuid4

import pytest

from app.api.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.domain.enums import Channel, EntityStatus
from app.domain.template import InvalidTemplateError, TemplateDefinition, TemplateRenderContext
from app.infrastructure.db.models import Project, Template
from app.services.template import TemplateService


class FakeSession:
    def __init__(self, projects: list[Project]):
        self.projects = projects

    async def get(self, model, object_id):
        if model is Project:
            return next((project for project in self.projects if project.id == object_id), None)
        return None

    async def commit(self):
        pass

    async def refresh(self, _template):
        return _template


class FakeTemplateRepository:
    def __init__(self, templates: list[Template], projects: list[Project]):
        self.templates = templates
        self.session = FakeSession(projects)
        self.last_filters = {}

    async def find_by_name(self, *, project_id, name, channel):
        return next(
            (
                template
                for template in self.templates
                if template.project_id == project_id
                and template.name == name
                and template.channel == channel
            ),
            None,
        )

    async def get_in_organization(self, *, template_id, organization_id):
        return next(
            (
                template
                for template in self.templates
                if template.id == template_id and template.organization_id == organization_id
            ),
            None,
        )

    async def create(self, template_data):
        template = Template(id=uuid4(), **template_data)
        self.templates.append(template)
        return template

    async def update(self, template_id, update_data):
        template = next(template for template in self.templates if template.id == template_id)
        for key, value in update_data.items():
            setattr(template, key, value)
        return template

    async def list_in_project(self, **filters):
        self.last_filters = filters
        return self.templates, len(self.templates)


class FakeAuditRepository:
    def __init__(self):
        self.events: list[dict] = []

    async def record(self, **event):
        self.events.append(event)


def make_project(*, organization_id=None, status=EntityStatus.ACTIVE):
    return Project(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        name="Kitchen",
        status=status,
    )


def make_template(*, organization_id, project_id, name="Reminder"):
    return Template(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        name=name,
        channel=Channel.WHATSAPP,
        body="Hi {{worker_name}}",
        variable_schema_json={"worker_name": "string"},
        status=EntityStatus.ACTIVE,
    )


def test_template_definition_rejects_undeclared_placeholders_and_renders_values():
    with pytest.raises(InvalidTemplateError, match="undeclared variables: worker_name"):
        TemplateDefinition(uuid4(), "Reminder", "Hi {{worker_name}}", {})

    template = TemplateDefinition(
        uuid4(),
        "Reminder",
        "Hi {{worker_name}}",
        {"worker_name": "string"},
    )
    assert template.render({"worker_name": "Asha"}) == "Hi Asha"


def test_template_context_renders_current_work_state_without_expression_execution():
    template = TemplateDefinition(
        uuid4(),
        "Work update",
        "{{project_name}} / {{department_name}}: {{work_status}} on {{date}}",
        {
            "project_name": "string",
            "department_name": "string",
            "work_status": "string",
            "date": "date",
        },
    )
    context = TemplateRenderContext(
        project_name="Kitchen",
        department_name="Install",
        current_date=date(2026, 9, 15),
        work_status="in_progress",
    )

    assert template.render_context(context) == "Kitchen / Install: in_progress on 2026-09-15"

    with pytest.raises(InvalidTemplateError, match="invalid placeholder"):
        TemplateDefinition(uuid4(), "Unsafe", "{{ project.name }}", {})


def test_template_context_missing_optional_state_fails_clearly():
    template = TemplateDefinition(
        uuid4(),
        "Contact update",
        "Contact: {{primary_contact_name}}",
        {"primary_contact_name": "string"},
    )
    context = TemplateRenderContext(
        project_name="Kitchen",
        department_name="Install",
        current_date=date(2026, 9, 15),
        work_status="open",
    )

    with pytest.raises(
        InvalidTemplateError, match="Missing template variables: primary_contact_name"
    ):
        template.render_context(context)


def test_body_parameters_follow_first_placeholder_order_not_schema_order():
    definition = TemplateDefinition(
        uuid4(),
        "Update",
        "{{department_name}} / {{project_name}} / {{department_name}}",
        {"project_name": "string", "department_name": "string"},
    )
    context = TemplateRenderContext(
        project_name="Apollo",
        department_name="Install",
        current_date=date(2026, 10, 7),
        work_status="in_progress",
    )

    assert definition.body_parameters(context) == ("Install", "Apollo")


@pytest.mark.asyncio
async def test_template_service_is_tenant_scoped_and_validates_project():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    repository = FakeTemplateRepository([], [project])
    service = TemplateService(repository)

    template = await service.create_template(
        organization_id=organization_id,
        project_id=project.id,
        actor_user_id=uuid4(),
        name="Reminder",
        channel=Channel.WHATSAPP,
        body="Hi {{worker_name}}",
        variable_schema={"worker_name": "string"},
    )

    assert template.organization_id == organization_id
    with pytest.raises(NotFoundError):
        await service.get_template(template_id=template.id, organization_id=uuid4())

    with pytest.raises(ConflictError):
        await service.create_template(
            organization_id=organization_id,
            project_id=project.id,
            actor_user_id=uuid4(),
            name="Reminder",
            channel=Channel.WHATSAPP,
            body="Hi {{worker_name}}",
            variable_schema={"worker_name": "string"},
        )


@pytest.mark.asyncio
async def test_archived_template_cannot_be_modified_or_reactivated():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    template = make_template(organization_id=organization_id, project_id=project.id)
    template.status = EntityStatus.ARCHIVED
    service = TemplateService(FakeTemplateRepository([template], [project]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.update_template(
            template_id=template.id,
            organization_id=organization_id,
            actor_user_id=uuid4(),
            update_data={"body": "Changed"},
        )
    assert exception_info.value.message == "Archived templates cannot be modified"


@pytest.mark.asyncio
async def test_template_service_renders_active_templates_and_rejects_archived_ones():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    template = make_template(organization_id=organization_id, project_id=project.id)
    template.body = "Hi {{primary_contact_name}}"
    template.variable_schema_json = {"primary_contact_name": "string"}
    service = TemplateService(FakeTemplateRepository([template], [project]))
    context = TemplateRenderContext(
        project_name="Kitchen",
        department_name="Install",
        current_date=date(2026, 9, 15),
        work_status="in_progress",
        primary_contact_name="Asha",
    )

    assert (
        await service.render_template(
            template_id=template.id,
            organization_id=organization_id,
            context=context,
        )
        == "Hi Asha"
    )

    template.status = EntityStatus.ARCHIVED
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.render_template(
            template_id=template.id,
            organization_id=organization_id,
            context=context,
        )
    assert exception_info.value.message == "Archived templates cannot be rendered"


@pytest.mark.asyncio
async def test_template_service_rejects_archived_project_and_invalid_definition():
    organization_id = uuid4()
    archived_project = make_project(organization_id=organization_id, status=EntityStatus.ARCHIVED)
    service = TemplateService(FakeTemplateRepository([], [archived_project]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_template(
            organization_id=organization_id,
            project_id=archived_project.id,
            actor_user_id=uuid4(),
            name="Reminder",
            channel=Channel.WHATSAPP,
            body="Hi {{worker_name}}",
            variable_schema={"worker_name": "string"},
        )
    assert exception_info.value.message == "Archived projects cannot contain new templates"

    project = make_project(organization_id=organization_id)
    service = TemplateService(FakeTemplateRepository([], [project]))
    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_template(
            organization_id=organization_id,
            project_id=project.id,
            actor_user_id=uuid4(),
            name="Reminder",
            channel=Channel.WHATSAPP,
            body="Hi {{worker_name}}",
            variable_schema={},
        )
    assert "undeclared variables: worker_name" in exception_info.value.message


@pytest.mark.asyncio
async def test_template_service_requires_provider_template_name_and_language_together():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    service = TemplateService(FakeTemplateRepository([], [project]))

    with pytest.raises(UnprocessableEntityError) as exception_info:
        await service.create_template(
            organization_id=organization_id,
            project_id=project.id,
            actor_user_id=uuid4(),
            name="Reminder",
            channel=Channel.WHATSAPP,
            body="Reminder",
            variable_schema={},
            provider_template_name="reminder_v1",
        )
    assert "must be configured together" in exception_info.value.message


@pytest.mark.asyncio
async def test_template_service_updates_valid_definition_and_records_audit():
    organization_id = uuid4()
    actor_user_id = uuid4()
    project = make_project(organization_id=organization_id)
    template = make_template(organization_id=organization_id, project_id=project.id)
    audit_repository = FakeAuditRepository()
    service = TemplateService(FakeTemplateRepository([template], [project]), audit_repository)

    updated = await service.update_template(
        template_id=template.id,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        update_data={
            "name": "Project update",
            "body": "Hi {{worker_name}} for {{project_name}}",
            "variable_schema_json": {"worker_name": "string", "project_name": "string"},
        },
    )

    assert updated.name == "Project update"
    assert updated.variable_schema_json == {
        "worker_name": "string",
        "project_name": "string",
    }
    assert audit_repository.events[0]["actor_user_id"] == actor_user_id
    assert audit_repository.events[0]["metadata"]["name"] == "Project update"


@pytest.mark.asyncio
async def test_template_service_archive_is_idempotent_and_audited_once():
    organization_id = uuid4()
    project = make_project(organization_id=organization_id)
    template = make_template(organization_id=organization_id, project_id=project.id)
    audit_repository = FakeAuditRepository()
    service = TemplateService(FakeTemplateRepository([template], [project]), audit_repository)

    await service.archive_template(
        template_id=template.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
    )
    await service.archive_template(
        template_id=template.id,
        organization_id=organization_id,
        actor_user_id=uuid4(),
    )

    assert template.status == EntityStatus.ARCHIVED
    assert len(audit_repository.events) == 1
    assert audit_repository.events[0]["metadata"] == {"status": EntityStatus.ARCHIVED.value}
