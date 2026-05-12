"""Add senior grades and competencies.

Revision ID: 20260505_0006
Revises: 20260503_0005
Create Date: 2026-05-05 15:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260505_0006"
down_revision = "20260503_0005"
branch_labels = None
depends_on = None


GRADE_ROWS = [
    (10, "grade_10", "高一", "senior"),
    (11, "grade_11", "高二", "senior"),
    (12, "grade_12", "高三", "senior"),
]

COMPETENCY_ROWS = [
    ("mathematical_abstraction", "数学抽象", 10),
    ("logical_reasoning", "逻辑推理", 11),
    ("mathematical_modeling", "数学建模", 12),
    ("intuitive_imagination", "直观想象", 13),
    ("mathematical_operation", "数学运算", 14),
    ("data_analysis", "数据分析", 15),
]


def upgrade() -> None:
    bind = op.get_bind()

    grades = sa.table(
        "grades",
        sa.column("grade_index", sa.SmallInteger()),
        sa.column("grade_code", sa.String(length=32)),
        sa.column("grade_name", sa.String(length=64)),
        sa.column("edu_stage", sa.String(length=32)),
    )
    competencies = sa.table(
        "competencies",
        sa.column("code", sa.String(length=64)),
        sa.column("name", sa.String(length=64)),
        sa.column("display_order", sa.SmallInteger()),
    )

    for grade_index, grade_code, grade_name, edu_stage in GRADE_ROWS:
        exists = bind.execute(
            sa.text("SELECT 1 FROM grades WHERE grade_index = :grade_index LIMIT 1"),
            {"grade_index": grade_index},
        ).scalar()
        if exists:
            bind.execute(
                sa.text(
                    """
                    UPDATE grades
                    SET grade_code = :grade_code,
                        grade_name = :grade_name,
                        edu_stage = :edu_stage
                    WHERE grade_index = :grade_index
                    """
                ),
                {
                    "grade_index": grade_index,
                    "grade_code": grade_code,
                    "grade_name": grade_name,
                    "edu_stage": edu_stage,
                },
            )
        else:
            op.bulk_insert(
                grades,
                [
                    {
                        "grade_index": grade_index,
                        "grade_code": grade_code,
                        "grade_name": grade_name,
                        "edu_stage": edu_stage,
                    }
                ],
            )

    for code, name, display_order in COMPETENCY_ROWS:
        exists = bind.execute(
            sa.text("SELECT 1 FROM competencies WHERE code = :code LIMIT 1"),
            {"code": code},
        ).scalar()
        if exists:
            bind.execute(
                sa.text(
                    """
                    UPDATE competencies
                    SET name = :name,
                        display_order = :display_order
                    WHERE code = :code
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "display_order": display_order,
                },
            )
        else:
            op.bulk_insert(
                competencies,
                [
                    {
                        "code": code,
                        "name": name,
                        "display_order": display_order,
                    }
                ],
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM question_gold_competencies WHERE competency_id IN "
            "(SELECT id FROM competencies WHERE code IN :codes)"
        ).bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": [row[0] for row in COMPETENCY_ROWS]},
    )
    bind.execute(
        sa.text("DELETE FROM competencies WHERE code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": [row[0] for row in COMPETENCY_ROWS]},
    )
