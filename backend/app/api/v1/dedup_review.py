from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dedup_review import (
    DuplicateReviewDecisionRequest,
    DuplicateReviewDecisionResponse,
    DuplicateReviewItem,
)
from app.services.dedup_review_service import DedupReviewService

router = APIRouter()


@router.get("/candidates", response_model=list[DuplicateReviewItem])
async def list_duplicate_review_candidates(
    review_status: str | None = Query(default="PENDING"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[DuplicateReviewItem]:
    service = DedupReviewService(db)
    return service.list_candidates(review_status=review_status, limit=limit)


@router.post(
    "/candidates/{candidate_id}/approve",
    response_model=DuplicateReviewDecisionResponse,
)
async def approve_duplicate_candidate(
    candidate_id: int,
    payload: DuplicateReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> DuplicateReviewDecisionResponse:
    service = DedupReviewService(db)
    return service.approve_duplicate(
        candidate_id=candidate_id,
        reviewed_by_user_id=payload.reviewed_by_user_id,
    )


@router.post(
    "/candidates/{candidate_id}/reject",
    response_model=DuplicateReviewDecisionResponse,
)
async def reject_duplicate_candidate(
    candidate_id: int,
    payload: DuplicateReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> DuplicateReviewDecisionResponse:
    service = DedupReviewService(db)
    return service.reject_duplicate(
        candidate_id=candidate_id,
        reviewed_by_user_id=payload.reviewed_by_user_id,
    )
