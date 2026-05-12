from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.annotations import (
    AdminQuestionReviewOut,
    AdminPoolResetRequest,
    AdminPoolResetResponse,
    AdminReviewDecisionRequest,
    AdminSelectionRequest,
    AdminSelectionResponse,
    AnnotatorHistoryListResponse,
    AnnotationTaskListResponse,
    ClaimAnnotationRequest,
    ClaimAnnotationResponse,
    ClaimReviewTaskRequest,
    ClaimReviewTaskResponse,
    PoolSummaryResponse,
    ReviewTaskListResponse,
    SelectionStrategyItem,
    SelectionBatchRollbackRequest,
    SelectionBatchRollbackResponse,
    SelectionBatchSummaryOut,
    SubmitAnnotationRequest,
    SubmitAnnotationResponse,
    SubmitReviewTaskRequest,
    SubmitReviewTaskResponse,
    WorkspaceSummaryOut,
)
from app.schemas.pagination import PageMeta
from app.services.annotation_service import SELECTION_STRATEGIES, AnnotationService

router = APIRouter()


@router.get("/pools/summary", response_model=PoolSummaryResponse)
async def pool_summary(db: Session = Depends(get_db)) -> PoolSummaryResponse:
    return AnnotationService(db).pool_summary()


@router.get("/workspace-summary", response_model=WorkspaceSummaryOut)
async def get_workspace_summary(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
) -> WorkspaceSummaryOut:
    return AnnotationService(db).get_workspace_summary(user_id)


@router.get("/selection-strategies", response_model=list[SelectionStrategyItem])
async def list_selection_strategies() -> list[SelectionStrategyItem]:
    return [SelectionStrategyItem(**item) for item in SELECTION_STRATEGIES]


@router.post("/admin/select", response_model=AdminSelectionResponse)
def select_questions_for_annotation(
    payload: AdminSelectionRequest,
    db: Session = Depends(get_db),
) -> AdminSelectionResponse:
    return AnnotationService(db).select_questions(payload)


@router.get("/admin/selection-batches", response_model=list[SelectionBatchSummaryOut])
def list_selection_batches(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[SelectionBatchSummaryOut]:
    return AnnotationService(db).list_selection_batches(limit=limit)


@router.post("/admin/pools/reset", response_model=AdminPoolResetResponse)
def reset_annotation_pools(
    payload: AdminPoolResetRequest,
    db: Session = Depends(get_db),
) -> AdminPoolResetResponse:
    return AnnotationService(db).reset_annotation_pool(payload)


@router.post(
    "/admin/selection-batches/{batch_id}/rollback",
    response_model=SelectionBatchRollbackResponse,
)
def rollback_selection_batch(
    batch_id: int,
    payload: SelectionBatchRollbackRequest,
    db: Session = Depends(get_db),
) -> SelectionBatchRollbackResponse:
    return AnnotationService(db).rollback_selection_batch(batch_id, payload)


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
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.get("/history", response_model=AnnotatorHistoryListResponse)
async def list_my_annotation_history(
    annotator_user_id: int = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AnnotatorHistoryListResponse:
    items, total = AnnotationService(db).list_annotator_history(
        annotator_user_id=annotator_user_id,
        page=page,
        page_size=page_size,
    )
    return AnnotatorHistoryListResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/tasks/{task_id}/submit", response_model=SubmitAnnotationResponse)
async def submit_annotation(
    task_id: int,
    payload: SubmitAnnotationRequest,
    db: Session = Depends(get_db),
) -> SubmitAnnotationResponse:
    return AnnotationService(db).submit_annotation(task_id, payload)


@router.post("/review-tasks/claim", response_model=ClaimReviewTaskResponse)
async def claim_review_tasks(
    payload: ClaimReviewTaskRequest,
    db: Session = Depends(get_db),
) -> ClaimReviewTaskResponse:
    return AnnotationService(db).claim_review_tasks(payload)


@router.get("/review-tasks", response_model=ReviewTaskListResponse)
async def list_review_tasks(
    reviewer_user_id: int = Query(...),
    review_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ReviewTaskListResponse:
    items, total = AnnotationService(db).list_review_tasks(
        reviewer_user_id=reviewer_user_id,
        review_status=review_status,
        page=page,
        page_size=page_size,
    )
    return ReviewTaskListResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.post("/review-tasks/{review_task_id}/submit", response_model=SubmitReviewTaskResponse)
async def submit_review_task(
    review_task_id: int,
    payload: SubmitReviewTaskRequest,
    db: Session = Depends(get_db),
) -> SubmitReviewTaskResponse:
    return AnnotationService(db).submit_review_task(review_task_id, payload)


@router.get("/admin/questions/{question_id}/review", response_model=AdminQuestionReviewOut)
def get_admin_question_review(
    question_id: int,
    admin_user_id: int = Query(...),
    db: Session = Depends(get_db),
) -> AdminQuestionReviewOut:
    return AnnotationService(db).get_admin_question_review(question_id, admin_user_id)


@router.post("/admin/questions/{question_id}/approve", response_model=AdminQuestionReviewOut)
def approve_admin_question_review(
    question_id: int,
    payload: AdminReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> AdminQuestionReviewOut:
    return AnnotationService(db).approve_admin_question_review(question_id, payload)


@router.post("/admin/questions/{question_id}/reject", response_model=AdminQuestionReviewOut)
def reject_admin_question_review(
    question_id: int,
    payload: AdminReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> AdminQuestionReviewOut:
    return AnnotationService(db).reject_admin_question_review(question_id, payload)
