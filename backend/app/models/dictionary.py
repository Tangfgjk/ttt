from __future__ import annotations

from sqlalchemy import Boolean, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Grade(TimestampMixin, Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    grade_index: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    grade_code: Mapped[str | None] = mapped_column(String(32))
    grade_name: Mapped[str] = mapped_column(String(64), nullable=False)
    edu_stage: Mapped[str | None] = mapped_column(String(32))


class QuestionType(TimestampMixin, Base):
    __tablename__ = "question_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    base_type_index: Mapped[int | None] = mapped_column(Integer)
