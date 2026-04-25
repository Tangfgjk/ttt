from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.question import (
    Question,
    QuestionDedupFeature,
    QuestionDuplicateCandidate,
    QuestionExternalRef,
)


class QuestionDedupRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_question_by_external_ref(
        self,
        *,
        data_source_id: int,
        external_question_id: str,
    ) -> Question | None:
        stmt = (
            select(Question)
            .join(QuestionExternalRef, QuestionExternalRef.question_id == Question.id)
            .where(
                QuestionExternalRef.data_source_id == data_source_id,
                QuestionExternalRef.external_question_id == external_question_id,
            )
        )
        return self.db.scalar(stmt)

    def get_feature_by_content_hash(
        self,
        *,
        content_hash: str,
        subject_id: int,
        question_type_id: int | None,
        dedup_version: str,
    ) -> QuestionDedupFeature | None:
        stmt = (
            self._feature_query()
            .where(
                QuestionDedupFeature.content_hash == content_hash,
                QuestionDedupFeature.dedup_version == dedup_version,
                Question.subject_id == subject_id,
            )
            .limit(1)
        )
        if question_type_id is None:
            stmt = stmt.where(Question.question_type_id.is_(None))
        else:
            stmt = stmt.where(Question.question_type_id == question_type_id)
        return self.db.scalar(stmt)

    def list_feature_candidates(
        self,
        *,
        subject_id: int,
        question_type_id: int | None,
        dedup_version: str,
        stem_hash: str,
        answer_hash: str | None,
        limit: int = 200,
    ) -> list[QuestionDedupFeature]:
        stmt = self._feature_query().where(
            QuestionDedupFeature.dedup_version == dedup_version,
            Question.subject_id == subject_id,
        )
        if question_type_id is None:
            stmt = stmt.where(Question.question_type_id.is_(None))
        else:
            stmt = stmt.where(Question.question_type_id == question_type_id)

        hash_filters = [QuestionDedupFeature.stem_hash == stem_hash]
        if answer_hash:
            hash_filters.append(QuestionDedupFeature.answer_hash == answer_hash)

        stmt = stmt.where(or_(*hash_filters)).limit(limit)
        return list(self.db.scalars(stmt).unique())

    def get_feature_by_question(
        self,
        *,
        question_id: int,
        dedup_version: str,
    ) -> QuestionDedupFeature | None:
        stmt = (
            select(QuestionDedupFeature)
            .where(
                QuestionDedupFeature.question_id == question_id,
                QuestionDedupFeature.dedup_version == dedup_version,
            )
            .limit(1)
        )
        return self.db.scalar(stmt)

    def save_feature(self, feature: QuestionDedupFeature) -> QuestionDedupFeature:
        self.db.add(feature)
        self.db.flush()
        return feature

    def create_duplicate_candidate(
        self,
        candidate: QuestionDuplicateCandidate,
    ) -> QuestionDuplicateCandidate:
        stmt = select(QuestionDuplicateCandidate).where(
            QuestionDuplicateCandidate.source_record_id == candidate.source_record_id,
            QuestionDuplicateCandidate.candidate_question_id == candidate.candidate_question_id,
            QuestionDuplicateCandidate.match_type == candidate.match_type,
        )
        existing = self.db.scalar(stmt)
        if existing is not None:
            existing.confidence_score = candidate.confidence_score
            existing.comparison_snapshot = candidate.comparison_snapshot
            existing.review_status = "PENDING"
            self.db.flush()
            return existing

        self.db.add(candidate)
        self.db.flush()
        return candidate

    def _feature_query(self) -> Select[tuple[QuestionDedupFeature]]:
        return select(QuestionDedupFeature).join(
            Question,
            Question.id == QuestionDedupFeature.question_id,
        ).options(joinedload(QuestionDedupFeature.question))
