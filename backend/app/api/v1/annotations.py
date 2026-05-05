from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.annotations import (
    AdminSelectionRequest,
    AdminSelectionResponse,
    AnnotationTaskListResponse,
    AnnotationTaskOut,
    ClaimAnnotationRequest,
    ClaimAnnotationResponse,
    PoolSummaryResponse,
    SelectionStrategyItem,
    SubmitAnnotationRequest,
    SubmitAnnotationResponse,
)
from app.schemas.pagination import PageMeta
from app.services.annotation_service import SELECTION_STRATEGIES, AnnotationService

router = APIRouter()


@router.get("/pools/summary", response_model=PoolSummaryResponse)
async def pool_summary(db: Session = Depends(get_db)) -> PoolSummaryResponse:
    return AnnotationService(db).pool_summary()


@router.get("/selection-strategies", response_model=list[SelectionStrategyItem])
async def list_selection_strategies() -> list[SelectionStrategyItem]:
    return [SelectionStrategyItem(**item) for item in SELECTION_STRATEGIES]


@router.post("/admin/select", response_model=AdminSelectionResponse)
async def select_questions_for_annotation(
    payload: AdminSelectionRequest,
    db: Session = Depends(get_db),
) -> AdminSelectionResponse:
    return AnnotationService(db).select_questions(payload)


@router.post("/claim", response_model=ClaimAnnotationResponse)
async def claim_questions(
    payload: ClaimAnnotationRequest,
    db: Session = Depends(get_db),
) -> ClaimAnnotationResponse:
    return AnnotationService(db).claim_questions(payload)


@router.get("/tasks", response_model=AnnotationTaskListResponse)
async def list_my_annotation_tasks(
    user_id: int = Query(...),
    task_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AnnotationTaskListResponse:
    items, total = AnnotationService(db).list_tasks(
        user_id=user_id,
        task_status=task_status,
        page=page,
        page_size=page_size,
    )
    return AnnotationTaskListResponse(
        items=[AnnotationTaskOut.model_validate(item) for item in items],
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/tasks/{task_id}/submit", response_model=SubmitAnnotationResponse)
async def submit_annotation(
    task_id: int,
    payload: SubmitAnnotationRequest,
    db: Session = Depends(get_db),
) -> SubmitAnnotationResponse:
    return AnnotationService(db).submit_annotation(task_id, payload)
