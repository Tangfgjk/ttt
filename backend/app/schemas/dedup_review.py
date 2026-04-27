from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ReviewCandidateQuestion(BaseModel):
    question_id: int
    stem_text: str
    answer_text: str | None = None


class ReviewSourceRecordSummary(BaseModel):
    source_record_id: int
    import_batch_id: int
    batch_no: str
    data_source_code: str
    data_source_name: str
    source_record_key: str
    parse_status: str
    source_stem_text: str
    source_answer_text: str | None = None
    normalized_question_id: int | None = None


class DuplicateReviewItem(BaseModel):
    candidate_id: int
    review_status: str
    match_type: str
    confidence_score: Decimal
    comparison_snapshot: dict
    source_record: ReviewSourceRecordSummary
    candidate_question: ReviewCandidateQuestion
    reviewer_name: str | None = None
    reviewed_at: datetime | None = None


class DuplicateReviewDecisionRequest(BaseModel):
    reviewed_by_user_id: int


class DuplicateReviewDecisionResponse(BaseModel):
    message: str
    source_record_id: int
    normalized_question_id: int
    parse_status: str
    review_status: str
