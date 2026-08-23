"""constrain user role and status

Revision ID: e8a7c6d5b4f3
Revises: d2f4a1b8c901
Create Date: 2026-08-23 16:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e8a7c6d5b4f3"
down_revision: str | Sequence[str] | None = "d2f4a1b8c901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_users_role_admin",
        "users",
        "role IN ('admin')",
    )
    op.create_check_constraint(
        "ck_users_status",
        "users",
        "status IN ('active', 'inactive')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_status", "users", type_="check")
    op.drop_constraint("ck_users_role_admin", "users", type_="check")
