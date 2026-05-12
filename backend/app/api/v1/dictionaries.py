from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dictionary import (
    CognitiveLevelItem,
    CompetencyItem,
    DictionaryItem,
    GradeItem,
    KnowledgeTypeItem,
)
from app.services.dictionary_service import DictionaryService

router = APIRouter()


@router.get("/subjects", response_model=list[DictionaryItem])
async def list_subjects(db: Session = Depends(get_db)) -> list[DictionaryItem]:
    service = DictionaryService(db)
    return [DictionaryItem.model_validate(item) for item in service.list_subjects()]


@router.get("/grades", response_model=list[GradeItem])
async def list_grades(db: Session = Depends(get_db)) -> list[GradeItem]:
    service = DictionaryService(db)
    return [GradeItem.model_validate(item) for item in service.list_grades()]


@router.get("/question-types", response_model=list[DictionaryItem])
async def list_question_types(db: Session = Depends(get_db)) -> list[DictionaryItem]:
    service = DictionaryService(db)
    return [DictionaryItem.model_validate(item) for item in service.list_question_types()]


@router.get("/knowledge-types", response_model=list[KnowledgeTypeItem])
async def list_knowledge_types(db: Session = Depends(get_db)) -> list[KnowledgeTypeItem]:
    service = DictionaryService(db)
    return [KnowledgeTypeItem.model_validate(item) for item in service.list_knowledge_types()]


@router.get("/cognitive-levels", response_model=list[CognitiveLevelItem])
async def list_cognitive_levels(db: Session = Depends(get_db)) -> list[CognitiveLevelItem]:
    service = DictionaryService(db)
    return [CognitiveLevelItem.model_validate(item) for item in service.list_cognitive_levels()]


@router.get("/competencies", response_model=list[CompetencyItem])
async def list_competencies(db: Session = Depends(get_db)) -> list[CompetencyItem]:
    service = DictionaryService(db)
    return [CompetencyItem.model_validate(item) for item in service.list_competencies()]
