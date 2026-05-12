"""Add active learning training and prediction records.

Revision ID: 20260506_0008
Revises: 20260505_0007
Create Date: 2026-05-06 10:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "20260506_0008"
down_revision = "20260505_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("model_training_runs"):
        op.create_table(
            "model_training_runs",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("run_no", sa.String(length=64), nullable=False, unique=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column(
                "triggered_by_user_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("users.id"),
            ),
            sa.Column("base_model_path", sa.String(length=512), nullable=False),
            sa.Column(
                "target_stage",
                sa.String(length=32),
                nullable=False,
                server_default="junior",
            ),
            sa.Column("train_sample_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("val_sample_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("params_json", sa.JSON()),
            sa.Column("metrics_json", sa.JSON()),
            sa.Column("error_message", sa.Text()),
            sa.Column("started_at", sa.DateTime()),
            sa.Column("finished_at", sa.DateTime()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not inspector.has_table("model_training_epochs"):
        op.create_table(
            "model_training_epochs",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column(
                "training_run_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("model_training_runs.id"),
                nullable=False,
            ),
            sa.Column("epoch_no", sa.SmallInteger(), nullable=False),
            sa.Column("train_loss", sa.Numeric(12, 6)),
            sa.Column("val_loss", sa.Numeric(12, 6)),
            sa.Column("level_accuracy", sa.Numeric(8, 6)),
            sa.Column("macro_f1", sa.Numeric(8, 6)),
            sa.Column("detection_rate", sa.Numeric(8, 6)),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not inspector.has_table("model_versions"):
        op.create_table(
            "model_versions",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("version_code", sa.String(length=32), nullable=False, unique=True),
            sa.Column(
                "training_run_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("model_training_runs.id"),
                nullable=False,
            ),
            sa.Column("checkpoint_path", sa.String(length=512), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("level_accuracy", sa.Numeric(8, 6)),
            sa.Column("macro_f1", sa.Numeric(8, 6)),
            sa.Column("detection_rate", sa.Numeric(8, 6)),
            sa.Column("val_loss", sa.Numeric(12, 6)),
            sa.Column("train_sample_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("val_sample_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("params_json", sa.JSON()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("model_versions")}
        if "training_run_id" not in columns:
            op.add_column(
                "model_versions",
                sa.Column(
                    "training_run_id",
                    mysql.BIGINT(unsigned=True),
                    sa.ForeignKey("model_training_runs.id"),
                    nullable=True,
                ),
            )
        if "checkpoint_path" not in columns:
            op.add_column(
                "model_versions",
                sa.Column("checkpoint_path", sa.String(length=512), nullable=True),
            )
            if "artifact_path" in columns:
                op.execute(
                    sa.text(
                        "UPDATE model_versions "
                        "SET checkpoint_path = artifact_path "
                        "WHERE checkpoint_path IS NULL"
                    )
                )
        if "is_active" not in columns:
            op.add_column(
                "model_versions",
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            )
        if "level_accuracy" not in columns:
            op.add_column("model_versions", sa.Column("level_accuracy", sa.Numeric(8, 6)))
        if "macro_f1" not in columns:
            op.add_column("model_versions", sa.Column("macro_f1", sa.Numeric(8, 6)))
        if "detection_rate" not in columns:
            op.add_column("model_versions", sa.Column("detection_rate", sa.Numeric(8, 6)))
        if "val_loss" not in columns:
            op.add_column("model_versions", sa.Column("val_loss", sa.Numeric(12, 6)))
        if "train_sample_count" not in columns:
            op.add_column(
                "model_versions",
                sa.Column("train_sample_count", sa.Integer(), nullable=False, server_default="0"),
            )
        if "val_sample_count" not in columns:
            op.add_column(
                "model_versions",
                sa.Column("val_sample_count", sa.Integer(), nullable=False, server_default="0"),
            )
        if "params_json" not in columns:
            op.add_column("model_versions", sa.Column("params_json", sa.JSON()))

    if not inspector.has_table("model_prediction_runs"):
        op.create_table(
            "model_prediction_runs",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column("run_no", sa.String(length=64), nullable=False, unique=True),
            sa.Column(
                "model_version_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("model_versions.id"),
                nullable=False,
            ),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column(
                "triggered_by_user_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("users.id"),
            ),
            sa.Column("confidence_strategy", sa.String(length=64), nullable=False),
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
        )

    if not inspector.has_table("model_prediction_items"):
        op.create_table(
            "model_prediction_items",
            sa.Column("id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
            sa.Column(
                "prediction_run_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("model_prediction_runs.id"),
                nullable=False,
            ),
            sa.Column(
                "question_id",
                mysql.BIGINT(unsigned=True),
                sa.ForeignKey("questions.id"),
                nullable=False,
            ),
            sa.Column("predicted_levels_json", sa.JSON(), nullable=False),
            sa.Column("probabilities_json", sa.JSON(), nullable=False),
            sa.Column("confidence_score", sa.Numeric(8, 6), nullable=False),
            sa.Column("uncertainty_score", sa.Numeric(8, 6), nullable=False),
            sa.Column("rank_no", sa.Integer(), nullable=False),
            sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    inspector = sa.inspect(bind)
    for table_name, index_name, columns in [
        ("model_training_runs", "ix_model_training_runs_status", ["status", "created_at"]),
        ("model_training_epochs", "ix_model_training_epochs_run", ["training_run_id", "epoch_no"]),
        ("model_versions", "ix_model_versions_active", ["is_active", "created_at"]),
        ("model_prediction_runs", "ix_model_prediction_runs_status", ["status", "created_at"]),
        (
            "model_prediction_items",
            "ix_model_prediction_items_run_rank",
            ["prediction_run_id", "rank_no"],
        ),
    ]:
        table_columns = {column["name"] for column in inspector.get_columns(table_name)}
        if any(column not in table_columns for column in columns):
            continue
        existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade() -> None:
    op.drop_index("ix_model_prediction_items_run_rank", table_name="model_prediction_items")
    op.drop_index("ix_model_prediction_runs_status", table_name="model_prediction_runs")
    op.drop_index("ix_model_versions_active", table_name="model_versions")
    op.drop_index("ix_model_training_epochs_run", table_name="model_training_epochs")
    op.drop_index("ix_model_training_runs_status", table_name="model_training_runs")
    op.drop_table("model_prediction_items")
    op.drop_table("model_prediction_runs")
    op.drop_table("model_versions")
    op.drop_table("model_training_epochs")
    op.drop_table("model_training_runs")
