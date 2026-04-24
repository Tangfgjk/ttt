from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class CognitiveLevel(TimestampMixin, Base):
    __tablename__ = "cognitive_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    level_order: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)


class Competency(TimestampMixin, Base):
    __tablename__ = "competencies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)


class KnowledgeType(TimestampMixin, Base):
    __tablename__ = "knowledge_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_type_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_type_name: Mapped[str] = mapped_column(String(64), nullable=False)

    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(back_populates="knowledge_type")


class KnowledgePoint(TimestampMixin, Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_knowledge_id: Mapped[str | None] = mapped_column(String(64))
    knowledge_type_id: Mapped[int] = mapped_column(ForeignKey("knowledge_types.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_points.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    knowledge_type: Mapped["KnowledgeType"] = relationship(back_populates="knowledge_points")
    parent: Mapped["KnowledgePoint | None"] = relationship(
        remote_side="KnowledgePoint.id",
        back_populates="children",
    )
    children: Mapped[list["KnowledgePoint"]] = relationship(back_populates="parent")


class Textbook(TimestampMixin, Base):
    __tablename__ = "textbooks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_textbook_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))

    catalogs: Mapped[list["Catalog"]] = relationship(back_populates="textbook")


class Catalog(TimestampMixin, Base):
    __tablename__ = "catalogs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_catalog_id: Mapped[str | None] = mapped_column(String(64))
    textbook_id: Mapped[int | None] = mapped_column(ForeignKey("textbooks.id"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("catalogs.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    school_code: Mapped[str | None] = mapped_column(String(32))

    textbook: Mapped["Textbook | None"] = relationship(back_populates="catalogs")
    parent: Mapped["Catalog | None"] = relationship(
        remote_side="Catalog.id",
        back_populates="children",
    )
    children: Mapped[list["Catalog"]] = relationship(back_populates="parent")
