from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.question_dedup_repository import QuestionDedupRepository
from app.schemas.dedup_review import (
    BulkApproveDuplicateResponse,
    DuplicateReviewDecisionResponse,
    DuplicateReviewItem,
    ReviewCandidateQuestion,
    ReviewSourceRecordSummary,
)
from app.services.import_service import ImportService
from app.services.question_content_hydrator import compose_dataset2_stem


class DedupReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = QuestionDedupRepository(db)
        self.import_service = ImportService(db)

    def list_candidates(
        self,
        *,
        review_status: str | None = "PENDING",
        limit: int = 100,
    ) -> list[DuplicateReviewItem]:
        items = self.repository.list_duplicate_candidates(review_status=review_status, limit=limit)
        return [self._serialize_candidate(item) for item in items]

    def approve_duplicate(
        self,
        *,
        candidate_id: int,
        reviewed_by_user_id: int,
    ) -> DuplicateReviewDecisionResponse:
        candidate = self._require_candidate(candidate_id)
        reviewer = self._require_user(reviewed_by_user_id)
        question = self._approve_candidate(candidate, reviewer.id)
        self.db.commit()

        return DuplicateReviewDecisionResponse(
            message="Duplicate candidate approved.",
            source_record_id=candidate.source_record_id,
            normalized_question_id=question.id,
            parse_status=candidate.source_record.parse_status,
            review_status="APPROVED",
        )

    def reject_duplicate(
        self,
        *,
        candidate_id: int,
        reviewed_by_user_id: int,
    ) -> DuplicateReviewDecisionResponse:
        candidate = self._require_candidate(candidate_id)
        reviewer = self._require_user(reviewed_by_user_id)
        reviewed_at = datetime.utcnow()

        question = self.import_service.materialize_source_record_as_new_question(
            candidate.source_record
        )
        self.repository.mark_related_candidates(
            source_record_id=candidate.source_record_id,
            winner_candidate_id=candidate.id,
            reviewed_by=reviewer.id,
            reviewed_at=reviewed_at,
            winner_status="REJECTED",
        )
        self.db.commit()

        return DuplicateReviewDecisionResponse(
            message="Duplicate candidate rejected and a new question was created.",
            source_record_id=candidate.source_record_id,
            normalized_question_id=question.id,
            parse_status=candidate.source_record.parse_status,
            review_status="REJECTED",
        )

    def bulk_approve_duplicates(
        self,
        *,
        reviewed_by_user_id: int,
        similarity_threshold: float,
    ) -> BulkApproveDuplicateResponse:
        reviewer = self._require_admin(reviewed_by_user_id)
        candidates = self.repository.list_pending_candidates_by_threshold(
            similarity_threshold=similarity_threshold
        )
        reviewed_source_record_ids: set[int] = set()
        approved_count = 0

        for candidate in candidates:
            if candidate.source_record_id in reviewed_source_record_ids:
                continue
            self._approve_candidate(candidate, reviewer.id)
            reviewed_source_record_ids.add(candidate.source_record_id)
            approved_count += 1

        self.db.commit()
        return BulkApproveDuplicateResponse(
            message="Bulk duplicate approval completed.",
            similarity_threshold=similarity_threshold,
            matched_candidate_count=len(candidates),
            approved_source_record_count=approved_count,
        )

    def _require_candidate(self, candidate_id: int):
        candidate = self.repository.get_duplicate_candidate(candidate_id)
        if candidate is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Duplicate candidate not found.",
            )
        return candidate

    def _require_user(self, user_id: int):
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reviewer user not found.",
            )
        return user

    def _require_admin(self, user_id: int):
        user = self._require_user(user_id)
        if user.role.code != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin users can bulk approve duplicate candidates.",
            )
        return user

    def _approve_candidate(self, candidate, reviewer_id: int):
        reviewed_at = datetime.utcnow()
        question = self.import_service.attach_source_record_to_existing_question(
            candidate.source_record,
            question_id=candidate.candidate_question_id,
        )
        self.repository.mark_related_candidates(
            source_record_id=candidate.source_record_id,
            winner_candidate_id=candidate.id,
            reviewed_by=reviewer_id,
            reviewed_at=reviewed_at,
            winner_status="APPROVED",
        )
        return question

    def _serialize_candidate(self, candidate) -> DuplicateReviewItem:
        source_record = candidate.source_record
        raw_payload = source_record.raw_payload or {}
        candidate_question = candidate.candidate_question
        candidate_content = candidate_question.content

        source_stem_text = (
            compose_dataset2_stem(raw_payload)[0]
            or raw_payload.get("question")
            or raw_payload.get("question_text")
            or raw_payload.get("题目内容")
            or raw_payload.get("题干（子题）")
            or ""
        )
        source_answer_text = (
            raw_payload.get("queAns")
            or raw_payload.get("answer")
            or raw_payload.get("question_answer")
            or raw_payload.get("题目答案")
        )

        return DuplicateReviewItem(
            candidate_id=candidate.id,
            review_status=candidate.review_status,
            match_type=candidate.match_type,
            confidence_score=candidate.confidence_score,
            comparison_snapshot=candidate.comparison_snapshot,
            source_record=ReviewSourceRecordSummary(
                source_record_id=source_record.id,
                import_batch_id=source_record.import_batch_id,
                batch_no=source_record.import_batch.batch_no,
                data_source_code=source_record.data_source.code,
                data_source_name=source_record.data_source.name,
                source_record_key=source_record.source_record_key,
                parse_status=source_record.parse_status,
                source_stem_text=str(source_stem_text),
                source_answer_text=str(source_answer_text) if source_answer_text else None,
                normalized_question_id=source_record.normalized_question_id,
            ),
            candidate_question=ReviewCandidateQuestion(
                question_id=candidate_question.id,
                stem_text=candidate_content.stem_text if candidate_content else "",
                answer_text=candidate_content.answer_text if candidate_content else None,
            ),
            reviewer_name=candidate.reviewer.real_name or candidate.reviewer.username
            if candidate.reviewer
            else None,
            reviewed_at=candidate.reviewed_at,
        )
