"""Create a large, synthetic dataset in the isolated local load-test database."""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, time, timedelta
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.security import hash_password
from app.domain.enums import (
    Channel,
    CommunicationJobStatus,
    ConsentStatus,
    DeliveryStatus,
    EntityStatus,
    OrganizationStatus,
    ScheduleStatus,
    SubscriptionStatus,
    WorkerStatus,
    WorkPriority,
    WorkStatus,
)
from app.infrastructure.db.models import (
    CommunicationJob,
    CommunicationJobStatusHistory,
    Department,
    Message,
    MessageStatusHistory,
    Organization,
    Project,
    Schedule,
    Template,
    User,
    Worker,
    WorkItem,
    WorkItemStatusHistory,
)

EXPECTED_HOST = "127.0.0.1"
EXPECTED_PORT = 55432
EXPECTED_DATABASE = "workpulse_loadtest"
PROJECT_COUNT = 6
OVERFLOW_PROJECT_COUNT = 120
DEPARTMENTS_PER_PROJECT = 4
WORKERS_PER_DEPARTMENT = 120
WORK_ITEMS_PER_DEPARTMENT = 180
MESSAGES_PER_DEPARTMENT = 100
JOBS_PER_DEPARTMENT = 100


def validate_database_url(database_url: str) -> None:
    parsed = urlparse(database_url)
    if (
        parsed.hostname != EXPECTED_HOST
        or parsed.port != EXPECTED_PORT
        or parsed.path.lstrip("/") != EXPECTED_DATABASE
    ):
        raise ValueError(
            "Refusing to seed anything except "
            f"{EXPECTED_HOST}:{EXPECTED_PORT}/{EXPECTED_DATABASE}."
        )


def new_work_item(
    organization_id: UUID,
    project_id: UUID,
    department_id: UUID,
    worker_id: UUID | None,
    index: int,
) -> WorkItem:
    statuses = tuple(WorkStatus)
    priorities = tuple(WorkPriority)
    return WorkItem(
        id=uuid4(),
        organization_id=organization_id,
        project_id=project_id,
        department_id=department_id,
        worker_id=worker_id,
        title=f"Load-test work item {index:05d}",
        description=f"Synthetic backlog record {index:05d} for list and filter testing.",
        priority=priorities[index % len(priorities)],
        status=statuses[index % len(statuses)],
        due_at=datetime.now(UTC) + timedelta(days=(index % 60) - 30),
    )


def seed(database_url: str) -> dict[str, int]:
    engine = create_engine(database_url, pool_pre_ping=True)
    counts: dict[str, int] = {}
    try:
        with Session(engine) as session, session.begin():
            existing = session.scalar(select(func.count()).select_from(Organization)) or 0
            if existing:
                raise RuntimeError(
                    f"Database already has {existing} organizations; refusing to append duplicate data."
                )

            organization = Organization(
                id=uuid4(),
                name="WorkPulse Load Test",
                slug="workpulse-load-test",
                status=OrganizationStatus.ACTIVE,
                subscription_status=SubscriptionStatus.ACTIVE,
            )
            session.add(organization)
            session.flush()

            admin = User(
                id=uuid4(),
                organization_id=organization.id,
                email="loadtest-admin@example.com",
                password_hash=hash_password("LoadTest!WorkPulse2026"),
                role="admin",
                status="active",
            )
            session.add(admin)
            session.flush()

            projects: list[Project] = []
            departments: list[Department] = []
            workers_by_department: list[list[Worker]] = []
            work_items_by_department: list[list[WorkItem]] = []
            templates: list[Template] = []
            schedules: list[Schedule] = []
            worker_number = 0
            work_item_number = 0

            for project_number in range(PROJECT_COUNT):
                project = Project(
                    id=UUID(int=project_number + 1),
                    organization_id=organization.id,
                    name=f"Load Test Project {project_number + 1:02d}",
                    description="Synthetic data for local UI and API volume validation.",
                    status=EntityStatus.ACTIVE,
                    start_date=date.today() - timedelta(days=120),
                    end_date=None,
                )
                projects.append(project)
                session.add(project)
                session.flush()

                for department_number in range(DEPARTMENTS_PER_PROJECT):
                    department = Department(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        name=f"Load Test Department {project_number + 1:02d}-{department_number + 1:02d}",
                        status=EntityStatus.ACTIVE,
                    )
                    departments.append(department)
                    session.add(department)
                    session.flush()

                    workers: list[Worker] = []
                    for department_worker in range(WORKERS_PER_DEPARTMENT):
                        worker_number += 1
                        worker = Worker(
                            id=uuid4(),
                            organization_id=organization.id,
                            department_id=department.id,
                            full_name=f"Load Worker {worker_number:05d}",
                            phone_number=f"+1555{worker_number:07d}",
                            contact_channel=Channel.WHATSAPP,
                            consent_status=(
                                ConsentStatus.OPTED_OUT
                                if department_worker % 7 == 0
                                else ConsentStatus.OPTED_IN
                            ),
                            status=(
                                WorkerStatus.INACTIVE
                                if department_worker % 25 == 0
                                else WorkerStatus.ACTIVE
                            ),
                        )
                        workers.append(worker)
                    workers_by_department.append(workers)
                    session.add_all(workers)
                    session.flush()

                    items = [
                        new_work_item(
                            organization.id,
                            project.id,
                            department.id,
                            workers[index % len(workers)].id if index % 8 else None,
                            work_item_number + index,
                        )
                        for index in range(WORK_ITEMS_PER_DEPARTMENT)
                    ]
                    work_item_number += WORK_ITEMS_PER_DEPARTMENT
                    work_items_by_department.append(items)
                    session.add_all(items)
                    session.flush()
                    session.add_all(
                        WorkItemStatusHistory(
                            id=uuid4(),
                            organization_id=organization.id,
                            work_item_id=item.id,
                            previous_status=WorkStatus.OPEN,
                            new_status=item.status,
                            actor_user_id=admin.id,
                            reason="Synthetic load-test status history.",
                        )
                        for index, item in enumerate(items)
                        if index % 20 == 0
                    )
                    session.flush()

                    template = Template(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        name=f"Load Test Template {project_number + 1:02d}-{department_number + 1:02d}",
                        channel=Channel.WHATSAPP,
                        body="Hello {{name}}, your synthetic update is ready.",
                        variable_schema_json={"name": "string"},
                        status=EntityStatus.ACTIVE,
                        created_by_user_id=admin.id,
                    )
                    templates.append(template)
                    session.add(template)
                    session.flush()

                    schedule = Schedule(
                        id=uuid4(),
                        organization_id=organization.id,
                        project_id=project.id,
                        department_id=department.id,
                        template_id=template.id,
                        timezone="UTC",
                        window_start_local=time(9, 0),
                        window_end_local=time(17, 0),
                        interval_seconds=86400,
                        status=ScheduleStatus.PAUSED,
                        next_run_at_utc=None,
                    )
                    schedules.append(schedule)
                    session.add(schedule)
                    session.flush()

                    opted_in_workers = [
                        worker
                        for worker in workers
                        if worker.consent_status == ConsentStatus.OPTED_IN
                        and worker.status == WorkerStatus.ACTIVE
                    ]
                    for local_index in range(MESSAGES_PER_DEPARTMENT):
                        worker = opted_in_workers[local_index % len(opted_in_workers)]
                        item = items[local_index % len(items)]
                        status = tuple(DeliveryStatus)[local_index % len(DeliveryStatus)]
                        created_at = datetime.now(UTC) - timedelta(minutes=local_index)
                        message = Message(
                            id=uuid4(),
                            organization_id=organization.id,
                            schedule_id=schedule.id,
                            work_item_id=item.id,
                            worker_id=worker.id,
                            channel=Channel.WHATSAPP,
                            recipient_phone_number=worker.phone_number,
                            rendered_body=f"Synthetic message {project_number}-{department_number}-{local_index}",
                            dispatch_key=f"loadtest-message-{project_number}-{department_number}-{local_index}",
                            delivery_status=status,
                            sent_at=created_at if status != DeliveryStatus.QUEUED else None,
                            delivered_at=(
                                created_at if status == DeliveryStatus.DELIVERED else None
                            ),
                            created_at=created_at,
                            updated_at=created_at,
                        )
                        session.add(message)
                        if local_index % 20 == 0:
                            session.add(
                                MessageStatusHistory(
                                    id=uuid4(),
                                    organization_id=organization.id,
                                    message_id=message.id,
                                    previous_status=None,
                                    new_status=status,
                                    provider_name="synthetic-load-test",
                                    created_at=created_at,
                                )
                            )

                    for local_index in range(JOBS_PER_DEPARTMENT):
                        worker = opted_in_workers[local_index % len(opted_in_workers)]
                        item = items[local_index % len(items)]
                        status = tuple(CommunicationJobStatus)[
                            local_index % len(CommunicationJobStatus)
                        ]
                        created_at = datetime.now(UTC) - timedelta(minutes=local_index)
                        job = CommunicationJob(
                            id=uuid4(),
                            organization_id=organization.id,
                            schedule_id=schedule.id,
                            template_id=template.id,
                            work_item_id=item.id,
                            worker_id=worker.id,
                            channel=Channel.WHATSAPP,
                            execution_at=created_at,
                            job_key=f"loadtest-job-{project_number}-{department_number}-{local_index}",
                            status=status,
                            attempt_count=1 if status == CommunicationJobStatus.FAILED else 0,
                            created_at=created_at,
                            updated_at=created_at,
                        )
                        session.add(job)
                        if local_index % 20 == 0:
                            session.add(
                                CommunicationJobStatusHistory(
                                    id=uuid4(),
                                    organization_id=organization.id,
                                    job_id=job.id,
                                    previous_status=None,
                                    new_status=status,
                                    reason="Synthetic load-test history.",
                                    created_at=created_at,
                                )
                            )

            overflow_projects = [
                Project(
                    id=UUID(int=(1 << 127) + project_number),
                    organization_id=organization.id,
                    name=f"Load Test Overflow Project {project_number + 1:03d}",
                    description="Synthetic project for picker pagination validation.",
                    status=EntityStatus.ACTIVE,
                    start_date=None,
                    end_date=None,
                )
                for project_number in range(OVERFLOW_PROJECT_COUNT)
            ]
            projects.extend(overflow_projects)
            session.add_all(overflow_projects)
            session.flush()
            counts = {
                "organizations": 1,
                "users": 1,
                "projects": len(projects),
                "departments": len(departments),
                "workers": worker_number,
                "work_items": work_item_number,
                "templates": len(templates),
                "schedules_paused": len(schedules),
                "messages": len(departments) * MESSAGES_PER_DEPARTMENT,
                "communication_jobs": len(departments) * JOBS_PER_DEPARTMENT,
                "history_rows": session.scalar(
                    select(func.count()).select_from(MessageStatusHistory)
                )
                + session.scalar(select(func.count()).select_from(CommunicationJobStatusHistory))
                + session.scalar(select(func.count()).select_from(WorkItemStatusHistory)),
            }
        return counts
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--confirm-isolated-loadtest-db", action="store_true")
    args = parser.parse_args()
    validate_database_url(args.database_url)
    if not args.confirm_isolated_loadtest_db:
        parser.error("Pass --confirm-isolated-loadtest-db to seed synthetic rows.")
    for table, count in seed(args.database_url).items():
        print(f"{table}: {count:,}")
    print("login: loadtest-admin@example.com / LoadTest!WorkPulse2026")


if __name__ == "__main__":
    main()
