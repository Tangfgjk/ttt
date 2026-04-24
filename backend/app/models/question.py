from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.dictionary import Catalog, Grade, KnowledgePoint, QuestionType, Subject
    from app.models.imports import DataSource


class Question(TimestampMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    grade_id: Mapped[int | None] = mapped_column(ForeignKey("grades.id"))
    question_type_id: Mapped[int | None] = mapped_column(ForeignKey("question_types.id"))
    difficulty_level: Mapped[int | None] = mapped_column(SmallInteger)
    blank_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    has_subquestions: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    annotation_status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    required_annotations: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    annotation_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    latest_embedding_version: Mapped[str | None] = mapped_column(String(64))

    subject: Mapped["Subject"] = relationship("Subject")
    grade: Mapped["Grade | None"] = relationship("Grade")
    question_type: Mapped["QuestionType | None"] = relationship("QuestionType")
    content: Mapped["QuestionContent"] = relationship(
        back_populates="question",
        uselist=False,
    )
    external_refs: Mapped[list["QuestionExternalRef"]] = relationship(back_populates="question")
    knowledge_points: Mapped[list["QuestionKnowledgePoint"]] = relationship(
        back_populates="question"
    )
    catalogs: Mapped[list["QuestionCatalog"]] = relationship(back_populates="question")


class QuestionContent(TimestampMixin, Base):
    __tablename__ = "question_contents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"),
        unique=True,
        nullable=False,
    )
    stem_text: Mapped[str] = mapped_column(Text, nullable=False)
    stem_html: Mapped[str | None] = mapped_column(Text)
    answer_text: Mapped[str | None] = mapped_column(Text)
    solution_text: Mapped[str | None] = mapped_column(Text)
    source_content_hash: Mapped[str | None] = mapped_column(String(64))

    question: Mapped["Question"] = relationship(back_populates="content")


class QuestionExternalRef(TimestampMixin, Base):
    __tablename__ = "question_external_refs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    external_question_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_type: Mapped[str | None] = mapped_column(String(32))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    question: Mapped["Question"] = relationship(back_populates="external_refs")
    data_source: Mapped["DataSource"] = relationship(back_populates="question_refs")


class QuestionKnowledgePoint(Base):
    __tablename__ = "question_knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    knowledge_point_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_points.id"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_exam_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_last_exam_point: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_index: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    question: Mapped["Question"] = relationship(back_populates="knowledge_points")
    knowledge_point: Mapped["KnowledgePoint"] = relationship("KnowledgePoint")


class QuestionCatalog(Base):
    __tablename__ = "question_catalogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    catalog_id: Mapped[int] = mapped_column(ForeignKey("catalogs.id"), nullable=False)
    school_code: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    question: Mapped["Question"] = relationship(back_populates="catalogs")
    catalog: Mapped["Catalog"] = relationship("Catalog")
