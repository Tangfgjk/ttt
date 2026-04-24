from __future__ import annotations

from sqlalchemy import ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"))
    question_type_id: Mapped[int | None] = mapped_column(ForeignKey("question_types.id"))
    difficulty_level: Mapped[int | None] = mapped_column(SmallInteger)
    blank_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    has_subquestions: Mapped[bool] = mapped_column(default=False, nullable=False)
    source_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    annotation_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    required_annotations: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    annotation_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    latest_embedding_version: Mapped[str | None] = mapped_column(String(64))

    content: Mapped["QuestionContent"] = relationship(back_populates="question", uselist=False)


class QuestionContent(TimestampMixin, Base):
    __tablename__ = "question_contents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), unique=True, nullable=False)
    stem_text: Mapped[str] = mapped_column(Text, nullable=False)
    stem_html: Mapped[str | None] = mapped_column(Text)
    answer_text: Mapped[str | None] = mapped_column(Text)
    solution_text: Mapped[str | None] = mapped_column(Text)
    source_content_hash: Mapped[str | None] = mapped_column(String(64))

    question: Mapped["Question"] = relationship(back_populates="content")
