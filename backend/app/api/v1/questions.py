from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.question_repository import QuestionFilters
from app.schemas.pagination import PageMeta
from app.schemas.question import (
    DifficultyLevelStatOut,
    ExternalRefOut,
    QuestionCatalogOut,
    QuestionDetailResponse,
    QuestionKnowledgePointOut,
    QuestionListItem,
    QuestionListResponse,
)
from app.services.question_service import QuestionService

router = APIRouter()


def _parse_question_ids(raw_value: str | None) -> list[int] | None:
    if not raw_value:
        return None
    parsed: list[int] = []
    for part in raw_value.split(","):
        value = part.strip()
        if not value:
            continue
        try:
            parsed_id = int(value)
        except ValueError:
            continue
        if parsed_id > 0:
            parsed.append(parsed_id)
    return parsed or None


def _build_question_list_item(question) -> QuestionListItem:
    return QuestionListItem.model_validate(question)


def _build_question_detail(
    question,
    *,
    source_difficulty_level: int | None,
    difficulty_level_stats: list[DifficultyLevelStatOut],
) -> QuestionDetailResponse:
    return QuestionDetailResponse(
        id=question.id,
        difficulty_level=question.difficulty_level,
        source_difficulty_level=source_difficulty_level,
        blank_count=question.blank_count,
        has_subquestions=question.has_subquestions,
        source_status=question.source_status,
        annotation_status=question.annotation_status,
        required_annotations=question.required_annotations,
        annotation_count=question.annotation_count,
        latest_embedding_version=question.latest_embedding_version,
        subject=question.subject,
        grade=question.grade,
        question_type=question.question_type,
        content=question.content,
        external_refs=[
            ExternalRefOut(
                id=item.id,
                external_question_id=item.external_question_id,
                external_type=item.external_type,
                is_primary=item.is_primary,
                data_source_code=item.data_source.code,
                data_source_name=item.data_source.name,
            )
            for item in question.external_refs
        ],
        knowledge_points=[
            QuestionKnowledgePointOut(
                id=item.id,
                knowledge_point_id=item.knowledge_point_id,
                knowledge_point_name=item.knowledge_point.name,
                priority=item.priority,
                is_core=item.is_core,
                is_exam_point=item.is_exam_point,
                is_last_exam_point=item.is_last_exam_point,
            )
            for item in question.knowledge_points
        ],
        catalogs=[
            QuestionCatalogOut(
                id=item.id,
                catalog_id=item.catalog_id,
                catalog_name=item.catalog.name,
                school_code=item.school_code,
            )
            for item in question.catalogs
        ],
        difficulty_level_stats=difficulty_level_stats,
    )


@router.get("/", response_model=QuestionListResponse)
async def list_questions(
    filter_question_id: int | None = Query(default=None, ge=1),
    keyword: str | None = Query(default=None),
    subject_id: int | None = Query(default=None),
    grade_id: int | None = Query(default=None),
    question_type_id: int | None = Query(default=None),
    annotation_status: str | None = Query(default=None),
    source_status: str | None = Query(default=None),
    question_ids: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> QuestionListResponse:
    service = QuestionService(db)
    filters = QuestionFilters(
        page=page,
        page_size=page_size,
        question_id=filter_question_id,
        keyword=keyword,
        subject_id=subject_id,
        grade_id=grade_id,
        question_type_id=question_type_id,
        annotation_status=annotation_status,
        source_status=source_status,
        question_ids=_parse_question_ids(question_ids),
    )
    items, total = service.list_questions(filters)
    return QuestionListResponse(
        items=[_build_question_list_item(item) for item in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/{question_id}", response_model=QuestionDetailResponse)
async def get_question_detail(
    question_id: int,
    db: Session = Depends(get_db),
) -> QuestionDetailResponse:
    service = QuestionService(db)
    question, source_difficulty_level, difficulty_level_stats = service.get_question_detail(question_id)
    return _build_question_detail(
        question,
        source_difficulty_level=source_difficulty_level,
        difficulty_level_stats=difficulty_level_stats,
    )
