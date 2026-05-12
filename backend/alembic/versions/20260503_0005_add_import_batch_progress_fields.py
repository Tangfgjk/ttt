"""Add import batch progress fields.

Revision ID: 20260503_0005
Revises: 20260425_0004
Create Date: 2026-05-03 20:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260503_0005"
down_revision = "20260425_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("import_batches")}

    if "total_file_count" not in columns:
        op.add_column(
            "import_batches",
            sa.Column("total_file_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if "uploaded_file_count" not in columns:
        op.add_column(
            "import_batches",
            sa.Column("uploaded_file_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if "processed_file_count" not in columns:
        op.add_column(
            "import_batches",
            sa.Column("processed_file_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if "expected_records" not in columns:
        op.add_column(
            "import_batches",
            sa.Column("expected_records", sa.Integer(), nullable=True),
        )
    if "processing_started_at" not in columns:
        op.add_column(
            "import_batches",
            sa.Column("processing_started_at", sa.DateTime(), nullable=True),
        )

    op.alter_column("import_batches", "total_file_count", server_default=None)
    op.alter_column("import_batches", "uploaded_file_count", server_default=None)
    op.alter_column("import_batches", "processed_file_count", server_default=None)


def downgrade() -> None:
    op.drop_column("import_batches", "processing_started_at")
    op.drop_column("import_batches", "expected_records")
    op.drop_column("import_batches", "processed_file_count")
    op.drop_column("import_batches", "uploaded_file_count")
    op.drop_column("import_batches", "total_file_count")
