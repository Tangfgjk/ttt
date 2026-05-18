"""Add user registration support fields.

Revision ID: 20260518_0012
Revises: 20260517_0011
Create Date: 2026-05-18 10:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260518_0012"
down_revision = "20260517_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}

    if "must_change_password" not in user_columns:
        op.add_column(
            "users",
            sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.alter_column("users", "must_change_password", server_default=None)

    if "last_login_at" not in user_columns:
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))

    if "email" in user_columns:
        op.alter_column(
            "users",
            "email",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("users")}

    if "email" in user_columns:
        op.alter_column(
            "users",
            "email",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    if "last_login_at" in user_columns:
        op.drop_column("users", "last_login_at")

    if "must_change_password" in user_columns:
        op.drop_column("users", "must_change_password")
