"""add department primary contact worker

Revision ID: f4c3a1b29d77
Revises: e8a7c6d5b4f3
Create Date: 2026-08-23 17:05:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f4c3a1b29d77"
down_revision = "e8a7c6d5b4f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "departments",
        sa.Column("primary_contact_worker_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_departments_primary_contact_worker",
        "departments",
        "workers",
        ["organization_id", "primary_contact_worker_id"],
        ["organization_id", "id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_departments_primary_contact_worker", "departments", type_="foreignkey")
    op.drop_column("departments", "primary_contact_worker_id")
