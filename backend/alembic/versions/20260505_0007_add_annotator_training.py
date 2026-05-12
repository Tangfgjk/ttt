"""Add annotator training scope and attempt records.

Revision ID: 20260505_0007
Revises: 20260505_0006
Create Date: 2026-05-05 17:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "20260505_0007"
down_revision = "20260505_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "training_scope" not in user_columns:
        op.add_column(
            "users",
            sa.Column("training_scope", sa.String(length=16), nullable=False, server_default="none"),
        )
        op.alter_column("users", "training_scope", server_default=None)

    if not inspector.has_table("annotator_training_attempts"):
        op.create_table(
            "annotator_training_attempts",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column(
                "user_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("edu_stage", sa.String(length=16), nullable=False),
            sa.Column("attempt_no", sa.SmallInteger(), nullable=False, server_default="1"),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("score_percent", sa.Numeric(5, 2), nullable=False),
            sa.Column("pass_threshold", sa.SmallInteger(), nullable=False, server_default="80"),
            sa.Column("total_questions", sa.SmallInteger(), nullable=False, server_default="0"),
            sa.Column("correct_questions", sa.SmallInteger(), nullable=False, server_default="0"),
            sa.Column("summary_json", sa.JSON(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=False),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("annotator_training_attempts")}
    if "ix_annotator_training_attempts_user_stage" not in existing_indexes:
        op.create_index(
            "ix_annotator_training_attempts_user_stage",
            "annotator_training_attempts",
            ["user_id", "edu_stage", "attempt_no"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_annotator_training_attempts_user_stage", table_name="annotator_training_attempts")
    op.drop_table("annotator_training_attempts")
    op.drop_column("users", "training_scope")
