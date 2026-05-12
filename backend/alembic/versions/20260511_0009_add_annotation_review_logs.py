"""Add annotation review logs.

Revision ID: 20260511_0009
Revises: 20260506_0008
Create Date: 2026-05-11 18:20:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "20260511_0009"
down_revision = "20260506_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("annotation_review_logs"):
        op.create_table(
            "annotation_review_logs",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column(
                "question_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("questions.id"),
                nullable=False,
            ),
            sa.Column(
                "aggregate_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("question_label_aggregates.id"),
            ),
            sa.Column(
                "review_task_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("review_tasks.id"),
            ),
            sa.Column(
                "actor_user_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("users.id"),
            ),
            sa.Column("actor_role", sa.String(length=32)),
            sa.Column("action_code", sa.String(length=64), nullable=False),
            sa.Column("comment", sa.Text()),
            sa.Column("detail_json", sa.JSON()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("annotation_review_logs")}
    if "ix_annotation_review_logs_question_created" not in existing_indexes:
        op.create_index(
            "ix_annotation_review_logs_question_created",
            "annotation_review_logs",
            ["question_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_annotation_review_logs_question_created", table_name="annotation_review_logs")
    op.drop_table("annotation_review_logs")
