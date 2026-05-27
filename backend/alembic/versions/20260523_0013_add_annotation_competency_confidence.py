"""Add per-competency annotation confidence levels.

Revision ID: 20260523_0013
Revises: 20260518_0012
Create Date: 2026-05-23 16:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260523_0013"
down_revision = "20260518_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("annotation_competencies")}

    if "confidence_level" not in columns:
        op.add_column(
            "annotation_competencies",
            sa.Column(
                "confidence_level",
                sa.SmallInteger(),
                nullable=False,
                server_default="5",
                comment="核心素养层级判断信心等级，1=低，3=中，5=高",
            ),
        )
        op.alter_column("annotation_competencies", "confidence_level", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("annotation_competencies")}

    if "confidence_level" in columns:
        op.drop_column("annotation_competencies", "confidence_level")
