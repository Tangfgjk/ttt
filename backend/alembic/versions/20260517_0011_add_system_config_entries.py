"""Add system config entries.

Revision ID: 20260517_0011
Revises: 20260511_0010
Create Date: 2026-05-17 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260517_0011"
down_revision = "20260511_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("system_config_entries"):
        op.create_table(
            "system_config_entries",
            sa.Column("config_key", sa.String(length=64), nullable=False),
            sa.Column("value_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("config_key", name="pk_system_config_entries"),
        )


def downgrade() -> None:
    op.drop_table("system_config_entries")
