"""Add question dedup support tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "20260425_0003"
down_revision = "20260424_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "question_dedup_features",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column(
            "question_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
            comment="题目ID",
        ),
        sa.Column(
            "normalized_stem_text",
            sa.Text(),
            nullable=False,
            comment="标准化后的题干文本",
        ),
        sa.Column(
            "normalized_answer_text",
            sa.Text(),
            nullable=True,
            comment="标准化后的答案文本",
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False, comment="内容指纹哈希"),
        sa.Column("stem_hash", sa.String(length=64), nullable=True, comment="题干哈希"),
        sa.Column("answer_hash", sa.String(length=64), nullable=True, comment="答案哈希"),
        sa.Column(
            "dedup_version",
            sa.String(length=32),
            nullable=False,
            server_default="v1",
            comment="判重规则版本",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "question_id",
            "dedup_version",
            name="uq_question_dedup_features_question_id_dedup_version",
        ),
        comment="题目判重特征表",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_question_dedup_features_content_hash",
        "question_dedup_features",
        ["content_hash"],
    )
    op.create_index(
        "ix_question_dedup_features_stem_hash",
        "question_dedup_features",
        ["stem_hash"],
    )
    op.create_index(
        "ix_question_dedup_features_answer_hash",
        "question_dedup_features",
        ["answer_hash"],
    )

    op.create_table(
        "question_duplicate_candidates",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column(
            "source_record_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
            comment="来源原始记录ID",
        ),
        sa.Column(
            "candidate_question_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
            comment="候选题目ID",
        ),
        sa.Column("match_type", sa.String(length=32), nullable=False, comment="候选命中类型"),
        sa.Column(
            "confidence_score",
            sa.Numeric(5, 4),
            nullable=False,
            comment="匹配置信分数",
        ),
        sa.Column(
            "comparison_snapshot",
            sa.JSON(),
            nullable=False,
            comment="比较快照JSON",
        ),
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING",
            comment="复核状态",
        ),
        sa.Column(
            "reviewed_by",
            mysql.BIGINT(unsigned=True),
            nullable=True,
            comment="复核人用户ID",
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="复核时间"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.ForeignKeyConstraint(["candidate_question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_question_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_record_id",
            "candidate_question_id",
            "match_type",
            name="uq_question_duplicate_candidates_source_candidate_type",
        ),
        comment="题目疑似重复候选表",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_question_duplicate_candidates_review_status",
        "question_duplicate_candidates",
        ["review_status"],
    )
    op.create_index(
        "ix_question_duplicate_candidates_source_record_id",
        "question_duplicate_candidates",
        ["source_record_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_question_duplicate_candidates_source_record_id",
        table_name="question_duplicate_candidates",
    )
    op.drop_index(
        "ix_question_duplicate_candidates_review_status",
        table_name="question_duplicate_candidates",
    )
    op.drop_table("question_duplicate_candidates")

    op.drop_index("ix_question_dedup_features_answer_hash", table_name="question_dedup_features")
    op.drop_index("ix_question_dedup_features_stem_hash", table_name="question_dedup_features")
    op.drop_index("ix_question_dedup_features_content_hash", table_name="question_dedup_features")
    op.drop_table("question_dedup_features")
