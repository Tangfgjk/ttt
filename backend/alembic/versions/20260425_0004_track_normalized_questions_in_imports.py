"""Track normalized question ids on source import records.

Revision ID: 20260425_0004
Revises: 20260425_0003
Create Date: 2026-04-25 16:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "20260425_0004"
down_revision = "20260425_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"]: item for item in inspector.get_columns("source_question_records")}
    foreign_keys = {item["name"] for item in inspector.get_foreign_keys("source_question_records")}

    if "normalized_question_id" not in columns:
        op.add_column(
            "source_question_records",
            sa.Column("normalized_question_id", mysql.BIGINT(unsigned=True), nullable=True),
        )

    existing_type = columns.get("normalized_question_id", {}).get("type", sa.BigInteger())
    op.alter_column(
        "source_question_records",
        "normalized_question_id",
        existing_type=existing_type,
        type_=mysql.BIGINT(unsigned=True),
        existing_nullable=True,
    )

    fk_name = "fk_source_question_records_normalized_question_id_questions"
    if fk_name not in foreign_keys:
        op.create_foreign_key(
            fk_name,
            "source_question_records",
            "questions",
            ["normalized_question_id"],
            ["id"],
        )


def downgrade() -> None:
    op.drop_constraint(
        "fk_source_question_records_normalized_question_id_questions",
        "source_question_records",
        type_="foreignkey",
    )
    op.drop_column("source_question_records", "normalized_question_id")
