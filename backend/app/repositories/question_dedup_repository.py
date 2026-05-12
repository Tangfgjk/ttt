from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.auth import User
from app.models.imports import SourceQuestionRecord
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

    def list_duplicate_candidates(
        self,
        *,
        review_status: str | None = "PENDING",
        limit: int = 100,
    ) -> list[QuestionDuplicateCandidate]:
        stmt = (
            select(QuestionDuplicateCandidate)
            .options(
                joinedload(QuestionDuplicateCandidate.source_record).joinedload(
                    SourceQuestionRecord.import_batch
                ),
                joinedload(QuestionDuplicateCandidate.source_record).joinedload(
                    SourceQuestionRecord.data_source
                ),
                joinedload(QuestionDuplicateCandidate.candidate_question).joinedload(
                    Question.content
                ),
                joinedload(QuestionDuplicateCandidate.reviewer),
            )
            .order_by(
                QuestionDuplicateCandidate.review_status.asc(),
                QuestionDuplicateCandidate.id.asc(),
            )
            .limit(limit)
        )
        if review_status:
            stmt = stmt.where(QuestionDuplicateCandidate.review_status == review_status)
        return list(self.db.scalars(stmt).unique())

    def get_duplicate_candidate(self, candidate_id: int) -> QuestionDuplicateCandidate | None:
        stmt = (
            select(QuestionDuplicateCandidate)
            .options(
                joinedload(QuestionDuplicateCandidate.source_record).joinedload(
                    SourceQuestionRecord.data_source
                ),
                joinedload(QuestionDuplicateCandidate.candidate_question).joinedload(
                    Question.content
                ),
            )
            .where(QuestionDuplicateCandidate.id == candidate_id)
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_user_by_id(self, user_id: int) -> User | None:
        stmt = select(User).options(joinedload(User.role)).where(User.id == user_id).limit(1)
        return self.db.scalar(stmt)

    def list_pending_candidates_by_threshold(
        self,
        *,
        similarity_threshold: float,
    ) -> list[QuestionDuplicateCandidate]:
        stmt = (
            select(QuestionDuplicateCandidate)
            .options(
                joinedload(QuestionDuplicateCandidate.source_record).joinedload(
                    SourceQuestionRecord.data_source
                ),
                joinedload(QuestionDuplicateCandidate.candidate_question).joinedload(
                    Question.content
                ),
            )
            .where(QuestionDuplicateCandidate.review_status == "PENDING")
            .where(QuestionDuplicateCandidate.confidence_score >= similarity_threshold)
            .order_by(
                QuestionDuplicateCandidate.source_record_id.asc(),
                QuestionDuplicateCandidate.confidence_score.desc(),
                QuestionDuplicateCandidate.id.asc(),
            )
        )
        return list(self.db.scalars(stmt).unique())

    def list_source_record_candidates(self, source_record_id: int) -> list[QuestionDuplicateCandidate]:
        stmt = (
            select(QuestionDuplicateCandidate)
            .options(selectinload(QuestionDuplicateCandidate.reviewer))
            .where(QuestionDuplicateCandidate.source_record_id == source_record_id)
        )
        return list(self.db.scalars(stmt))

    def save_duplicate_candidate(self, candidate: QuestionDuplicateCandidate) -> QuestionDuplicateCandidate:
        self.db.add(candidate)
        self.db.flush()
        return candidate

    def mark_related_candidates(
        self,
        *,
        source_record_id: int,
        winner_candidate_id: int,
        reviewed_by: int,
        reviewed_at: datetime,
        winner_status: str,
        loser_status: str = "DISMISSED",
    ) -> None:
        for item in self.list_source_record_candidates(source_record_id):
            if item.id == winner_candidate_id:
                item.review_status = winner_status
            else:
                item.review_status = loser_status
            item.reviewed_by = reviewed_by
            item.reviewed_at = reviewed_at
        self.db.flush()

    def _feature_query(self) -> Select[tuple[QuestionDedupFeature]]:
        return select(QuestionDedupFeature).join(
            Question,
            Question.id == QuestionDedupFeature.question_id,
        ).options(joinedload(QuestionDedupFeature.question))
