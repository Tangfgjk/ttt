from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.annotations import (
    AdminAggregateOverrideRequest,
    AdminAnnotatorTaskListResponse,
    AdminRecycleAnnotationTasksRequest,
    AdminRecycleAnnotationTasksResponse,
    AnnotationPolicySettingsOut,
    AnnotationPolicyUpdateRequest,
    AnnotationPolicyUpdateResponse,
    AdminQuestionReviewOut,
    AdminPoolResetRequest,
    AdminPoolResetResponse,
    AdminReviewDecisionRequest,
    AdminSelectionRequest,
    AdminSelectionResponse,
    AnnotatorHistoryAdoptionStatus,
    AnnotatorHistoryListResponse,
    AnnotatorHistoryReviewState,
    AnnotatorHistoryTimeRange,
    AnnotationTaskListResponse,
    AutoReconcileReviewTasksRequest,
    AutoReconcileReviewTasksResponse,
    ClaimAnnotationRequest,
    ClaimAnnotationResponse,
    ClaimReviewTaskRequest,
    ClaimReviewTaskResponse,
    PoolSummaryResponse,
    ReturnReviewTasksRequest,
    ReturnReviewTasksResponse,
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


@router.get("/admin/policy", response_model=AnnotationPolicySettingsOut)
async def get_annotation_policy(db: Session = Depends(get_db)) -> AnnotationPolicySettingsOut:
    return AnnotationService(db).get_annotation_policy()


@router.post("/admin/policy", response_model=AnnotationPolicyUpdateResponse)
async def update_annotation_policy(
    payload: AnnotationPolicyUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AnnotationPolicyUpdateResponse:
    service = AnnotationService(db)
    response = service.update_annotation_policy(payload)
    background_tasks.add_task(
        AnnotationService.apply_annotation_policy_to_idle_questions_async,
        int(payload.annotator_count),
    )
    return response


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
    keyword: str | None = Query(default=None),
    review_state: AnnotatorHistoryReviewState | None = Query(default=None),
    adoption_status: AnnotatorHistoryAdoptionStatus | None = Query(default=None),
    time_range: AnnotatorHistoryTimeRange | None = Query(default=None),
    db: Session = Depends(get_db),
) -> AnnotatorHistoryListResponse:
    items, total = AnnotationService(db).list_annotator_history(
        annotator_user_id=annotator_user_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        review_state=review_state,
        adoption_status=adoption_status,
        time_range=time_range,
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


@router.post("/tasks/{task_id}/revise", response_model=SubmitAnnotationResponse)
async def revise_annotation(
    task_id: int,
    payload: SubmitAnnotationRequest,
    db: Session = Depends(get_db),
) -> SubmitAnnotationResponse:
    return AnnotationService(db).revise_annotation(task_id, payload)


@router.post("/review-tasks/claim", response_model=ClaimReviewTaskResponse)
async def claim_review_tasks(
    payload: ClaimReviewTaskRequest,
    db: Session = Depends(get_db),
) -> ClaimReviewTaskResponse:
    return AnnotationService(db).claim_review_tasks(payload)


@router.post(
    "/review-tasks/reconcile-auto-consensus",
    response_model=AutoReconcileReviewTasksResponse,
)
async def reconcile_review_tasks_with_current_rules(
    payload: AutoReconcileReviewTasksRequest,
    db: Session = Depends(get_db),
) -> AutoReconcileReviewTasksResponse:
    return AnnotationService(db).reconcile_review_tasks_with_current_rules(payload)


@router.post(
    "/review-tasks/return-for-reannotation",
    response_model=ReturnReviewTasksResponse,
)
async def return_review_tasks_for_reannotation(
    payload: ReturnReviewTasksRequest,
    db: Session = Depends(get_db),
) -> ReturnReviewTasksResponse:
    return AnnotationService(db).return_my_review_tasks_for_reannotation(payload)


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


@router.get("/admin/annotator-tasks", response_model=AdminAnnotatorTaskListResponse)
def list_admin_annotator_tasks(
    admin_user_id: int = Query(...),
    task_status: str | None = Query(default="IN_PROGRESS"),
    annotator_user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AdminAnnotatorTaskListResponse:
    items, total = AnnotationService(db).list_admin_annotator_tasks(
        admin_user_id=admin_user_id,
        task_status=task_status,
        annotator_user_id=annotator_user_id,
        page=page,
        page_size=page_size,
    )
    return AdminAnnotatorTaskListResponse(
        items=items,
        meta=PageMeta(page=page, page_size=page_size, total=total),
    )


@router.post(
    "/admin/annotator-tasks/recycle",
    response_model=AdminRecycleAnnotationTasksResponse,
)
def recycle_admin_annotator_tasks(
    payload: AdminRecycleAnnotationTasksRequest,
    db: Session = Depends(get_db),
) -> AdminRecycleAnnotationTasksResponse:
    return AnnotationService(db).recycle_annotation_tasks(payload)


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


@router.post("/admin/questions/{question_id}/override", response_model=AdminQuestionReviewOut)
def override_admin_question_review(
    question_id: int,
    payload: AdminAggregateOverrideRequest,
    db: Session = Depends(get_db),
) -> AdminQuestionReviewOut:
    return AnnotationService(db).override_admin_question_review(question_id, payload)
