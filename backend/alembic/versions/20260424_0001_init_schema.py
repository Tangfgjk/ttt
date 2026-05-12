"""Initial schema for V2 project design.

This revision intentionally executes curated SQL files instead of expanding
49 tables into a single large `op.create_table(...)` script. That keeps the
first migration readable while still fitting Alembic's revision model.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260424_0001"
down_revision = None
branch_labels = None
depends_on = None


def _sql_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "sql"


def _load_statements(filename: str) -> list[str]:
    sql_path = _sql_dir() / filename
    text = sql_path.read_text(encoding="utf-8")

    statements: list[str] = []
    current: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("--"):
            continue

        current.append(raw_line)
        if line.endswith(";"):
            statement = "\n".join(current).strip()
            if statement.endswith(";"):
                statement = statement[:-1]
            statements.append(statement)
            current = []

    if current:
        statements.append("\n".join(current).strip())

    return statements


def _execute_sql_file(filename: str) -> None:
    for statement in _load_statements(filename):
        op.execute(statement)


def upgrade() -> None:
    _execute_sql_file("20260424_0001_upgrade.sql")


def downgrade() -> None:
    _execute_sql_file("20260424_0001_downgrade.sql")
