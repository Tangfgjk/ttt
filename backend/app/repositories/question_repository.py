from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.question import (
    Question,
    QuestionCatalog,
    QuestionContent,
    QuestionExternalRef,
    QuestionKnowledgePoint,
)


@dataclass
class QuestionFilters:
    page: int = 1
    page_size: int = 20
    keyword: str | None = None
    subject_id: int | None = None
    grade_id: int | None = None
    question_type_id: int | None = None
    annotation_status: str | None = None
    source_status: str | None = None


class QuestionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_questions(self, filters: QuestionFilters) -> tuple[list[Question], int]:
        stmt = self._base_query()
        stmt = self._apply_filters(stmt, filters)
        total = self._count(stmt)

        stmt = (
            stmt.order_by(Question.id.desc())
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )
        items = list(self.db.scalars(stmt).unique())
        return items, total

    def get_question_by_id(self, question_id: int) -> Question | None:
        stmt = self._base_query().where(Question.id == question_id)
        return self.db.scalar(stmt)

    def _base_query(self) -> Select[tuple[Question]]:
        return select(Question).options(
            selectinload(Question.subject),
            selectinload(Question.grade),
            selectinload(Question.question_type),
            selectinload(Question.content),
            selectinload(Question.external_refs).selectinload(QuestionExternalRef.data_source),
            selectinload(Question.knowledge_points).selectinload(QuestionKnowledgePoint.knowledge_point),
            selectinload(Question.catalogs).selectinload(QuestionCatalog.catalog),
        )

    def _apply_filters(
        self,
        stmt: Select[tuple[Question]],
        filters: QuestionFilters,
    ) -> Select[tuple[Question]]:
        if filters.keyword:
            # Querying against the content table keeps the list API useful even
            # before we introduce a dedicated search index.
            stmt = stmt.join(QuestionContent, QuestionContent.question_id == Question.id).where(
                QuestionContent.stem_text.ilike(f"%{filters.keyword}%")
            )
        if filters.subject_id:
            stmt = stmt.where(Question.subject_id == filters.subject_id)
        if filters.grade_id:
            stmt = stmt.where(Question.grade_id == filters.grade_id)
        if filters.question_type_id:
            stmt = stmt.where(Question.question_type_id == filters.question_type_id)
        if filters.annotation_status:
            stmt = stmt.where(Question.annotation_status == filters.annotation_status)
        if filters.source_status:
            stmt = stmt.where(Question.source_status == filters.source_status)
        return stmt

    def _count(self, stmt: Select[tuple[Question]]) -> int:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        return self.db.scalar(count_stmt) or 0
