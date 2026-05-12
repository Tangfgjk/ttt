from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dictionary import (
    CognitiveLevel,
    Competency,
    Grade,
    KnowledgeType,
    QuestionType,
    Subject,
)


class DictionaryRepository:
    """Read-only repository for stable dictionary data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_subjects(self) -> list[Subject]:
        stmt = select(Subject).order_by(Subject.id.asc())
        return list(self.db.scalars(stmt))

    def list_grades(self) -> list[Grade]:
        stmt = select(Grade).order_by(Grade.grade_index.asc())
        return list(self.db.scalars(stmt))

    def list_question_types(self) -> list[QuestionType]:
        stmt = select(QuestionType).order_by(QuestionType.id.asc())
        return list(self.db.scalars(stmt))

    def list_knowledge_types(self) -> list[KnowledgeType]:
        stmt = select(KnowledgeType).order_by(KnowledgeType.id.asc())
        return list(self.db.scalars(stmt))

    def list_cognitive_levels(self) -> list[CognitiveLevel]:
        stmt = select(CognitiveLevel).order_by(CognitiveLevel.level_order.asc())
        return list(self.db.scalars(stmt))

    def list_competencies(self) -> list[Competency]:
        stmt = select(Competency).order_by(Competency.display_order.asc())
        return list(self.db.scalars(stmt))
