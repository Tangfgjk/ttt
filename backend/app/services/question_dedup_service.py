from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.question import (
    Question,
    QuestionDedupFeature,
    QuestionDuplicateCandidate,
)
from app.repositories.question_dedup_repository import QuestionDedupRepository
from app.utils.question_dedup import (
    NormalizedQuestionText,
    build_question_fingerprint,
    compute_text_similarity,
)

DEFAULT_DEDUP_VERSION = "v1"
HIGH_CONFIDENCE_SIMILARITY = 0.98


@dataclass(frozen=True)
class DedupInput:
    subject_id: int
    question_type_id: int | None
    stem_text: str | None
    answer_text: str | None
    data_source_id: int | None = None
    external_question_id: str | None = None
    grade_id: int | None = None
    subquestion_count: int = 0
    knowledge_point_ids: tuple[int, ...] = ()
    source_record_id: int | None = None


@dataclass(frozen=True)
class DuplicateCandidateMatch:
    question_id: int
    match_type: str
    confidence_score: float
    snapshot: dict


@dataclass(frozen=True)
class DedupDecision:
    status: str
    question_id: int | None
    fingerprint: NormalizedQuestionText
    match_score: float | None = None
    match_snapshot: dict = field(default_factory=dict)
    candidates: tuple[DuplicateCandidateMatch, ...] = ()


class QuestionDedupService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = QuestionDedupRepository(db)

    def evaluate(
        self,
        payload: DedupInput,
        *,
        dedup_version: str = DEFAULT_DEDUP_VERSION,
    ) -> DedupDecision:
        fingerprint = build_question_fingerprint(
            stem_text=payload.stem_text,
            answer_text=payload.answer_text,
            subject_id=payload.subject_id,
            question_type_id=payload.question_type_id,
        )

        external_match = self._match_by_external_ref(payload)
        if external_match is not None:
            return DedupDecision(
                status="MATCHED_BY_EXTERNAL_ID",
                question_id=external_match.id,
                fingerprint=fingerprint,
                match_score=1.0,
                match_snapshot={
                    "data_source_id": payload.data_source_id,
                    "external_question_id": payload.external_question_id,
                },
            )

        content_match = self.repository.get_feature_by_content_hash(
            content_hash=fingerprint.content_hash,
            subject_id=payload.subject_id,
            question_type_id=payload.question_type_id,
            dedup_version=dedup_version,
        )
        if content_match is not None:
            return DedupDecision(
                status="MATCHED_BY_CONTENT_HASH",
                question_id=content_match.question_id,
                fingerprint=fingerprint,
                match_score=1.0,
                match_snapshot={
                    "question_id": content_match.question_id,
                    "content_hash": fingerprint.content_hash,
                },
            )

        candidates = self._build_candidates(
            payload,
            fingerprint=fingerprint,
            dedup_version=dedup_version,
        )
        if candidates:
            if payload.source_record_id is not None:
                self._persist_candidates(payload.source_record_id, candidates)
            return DedupDecision(
                status="PENDING_REVIEW",
                question_id=None,
                fingerprint=fingerprint,
                match_score=max(candidate.confidence_score for candidate in candidates),
                match_snapshot={"candidate_count": len(candidates)},
                candidates=tuple(candidates),
            )

        return DedupDecision(
            status="CREATED_NEW_QUESTION",
            question_id=None,
            fingerprint=fingerprint,
        )

    def sync_question_feature(
        self,
        question: Question,
        *,
        dedup_version: str = DEFAULT_DEDUP_VERSION,
    ) -> QuestionDedupFeature:
        content = question.content
        if content is None:
            raise ValueError("Question content is required before syncing dedup features.")

        fingerprint = build_question_fingerprint(
            stem_text=content.stem_text,
            answer_text=content.answer_text,
            subject_id=question.subject_id,
            question_type_id=question.question_type_id,
        )
        feature = self.repository.get_feature_by_question(
            question_id=question.id,
            dedup_version=dedup_version,
        )
        if feature is None:
            feature = QuestionDedupFeature(
                question_id=question.id,
                dedup_version=dedup_version,
                normalized_stem_text=fingerprint.normalized_stem_text,
                normalized_answer_text=fingerprint.normalized_answer_text,
                content_hash=fingerprint.content_hash,
                stem_hash=fingerprint.stem_hash,
                answer_hash=fingerprint.answer_hash,
            )
        else:
            feature.normalized_stem_text = fingerprint.normalized_stem_text
            feature.normalized_answer_text = fingerprint.normalized_answer_text
            feature.content_hash = fingerprint.content_hash
            feature.stem_hash = fingerprint.stem_hash
            feature.answer_hash = fingerprint.answer_hash
        return self.repository.save_feature(feature)

    def _match_by_external_ref(self, payload: DedupInput) -> Question | None:
        if not payload.data_source_id or not payload.external_question_id:
            return None
        return self.repository.get_question_by_external_ref(
            data_source_id=payload.data_source_id,
            external_question_id=payload.external_question_id,
        )

    def _build_candidates(
        self,
        payload: DedupInput,
        *,
        fingerprint: NormalizedQuestionText,
        dedup_version: str,
    ) -> list[DuplicateCandidateMatch]:
        raw_candidates = self.repository.list_feature_candidates(
            subject_id=payload.subject_id,
            question_type_id=payload.question_type_id,
            dedup_version=dedup_version,
            stem_hash=fingerprint.stem_hash,
            answer_hash=fingerprint.answer_hash,
        )
        candidates: list[DuplicateCandidateMatch] = []
        for feature in raw_candidates:
            stem_similarity = compute_text_similarity(
                fingerprint.normalized_stem_text,
                feature.normalized_stem_text,
            )
            if stem_similarity < HIGH_CONFIDENCE_SIMILARITY:
                continue

            answer_exact = (
                bool(fingerprint.answer_hash)
                and fingerprint.answer_hash == feature.answer_hash
            )
            if not answer_exact:
                continue

            question = feature.question
            grade_distance = self._grade_distance(payload.grade_id, question.grade_id)
            if grade_distance is not None and grade_distance > 1:
                continue

            snapshot = {
                "question_id": question.id,
                "stem_similarity": round(stem_similarity, 4),
                "answer_exact": answer_exact,
                "grade_distance": grade_distance,
                "content_hash_equal": fingerprint.content_hash == feature.content_hash,
            }
            candidates.append(
                DuplicateCandidateMatch(
                    question_id=question.id,
                    match_type="RULE_CANDIDATE",
                    confidence_score=stem_similarity,
                    snapshot=snapshot,
                )
            )
        candidates.sort(key=lambda item: item.confidence_score, reverse=True)
        return candidates

    def _persist_candidates(
        self,
        source_record_id: int,
        candidates: list[DuplicateCandidateMatch],
    ) -> None:
        for candidate in candidates:
            self.repository.create_duplicate_candidate(
                QuestionDuplicateCandidate(
                    source_record_id=source_record_id,
                    candidate_question_id=candidate.question_id,
                    match_type=candidate.match_type,
                    confidence_score=Decimal(f"{candidate.confidence_score:.4f}"),
                    comparison_snapshot=candidate.snapshot,
                )
            )

    @staticmethod
    def _grade_distance(left: int | None, right: int | None) -> int | None:
        if left is None or right is None:
            return None
        return abs(left - right)
