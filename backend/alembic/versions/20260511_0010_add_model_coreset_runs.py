"""Add model coreset runs.

Revision ID: 20260511_0010
Revises: 20260511_0009
Create Date: 2026-05-11 22:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "20260511_0010"
down_revision = "20260511_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("model_coreset_runs"):
        op.create_table(
            "model_coreset_runs",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("run_no", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column(
                "triggered_by_user_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("users.id"),
            ),
            sa.Column("strategy", sa.String(length=64), nullable=False),
            sa.Column("data_scope", sa.String(length=32), nullable=False),
            sa.Column("requested_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("selected_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("moved_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "recommendation_batch_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("recommendation_batches.id"),
            ),
            sa.Column("params_json", sa.JSON()),
            sa.Column("metrics_json", sa.JSON()),
            sa.Column("error_message", sa.Text()),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("finished_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("run_no", name="uq_model_coreset_runs_run_no"),
        )

    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("model_coreset_runs")}
    if "ix_model_coreset_runs_created_at" not in existing_indexes:
        op.create_index(
            "ix_model_coreset_runs_created_at",
            "model_coreset_runs",
            ["created_at"],
            unique=False,
        )
    if "ix_model_coreset_runs_status_created" not in existing_indexes:
        op.create_index(
            "ix_model_coreset_runs_status_created",
            "model_coreset_runs",
            ["status", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("ix_model_coreset_runs_status_created", table_name="model_coreset_runs")
    op.drop_index("ix_model_coreset_runs_created_at", table_name="model_coreset_runs")
    op.drop_table("model_coreset_runs")
