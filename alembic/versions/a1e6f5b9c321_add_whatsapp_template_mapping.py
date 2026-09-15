"""Add provider mapping fields to message templates.

Revision ID: a1e6f5b9c321
Revises: c9b2d7f4e1a0
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "a1e6f5b9c321"
down_revision = "c9b2d7f4e1a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("provider_template_name", sa.String(length=512), nullable=True))
    op.add_column("templates", sa.Column("provider_template_language", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("templates", "provider_template_language")
    op.drop_column("templates", "provider_template_name")