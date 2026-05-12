from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.auth import Role, User
from app.models.dictionary import Grade, QuestionType, Subject
from app.models.imports import DataSource, ImportBatch, SourceQuestionRecord
from app.models.question import Question, QuestionContent, QuestionDuplicateCandidate, QuestionExternalRef
from app.services.dedup_review_service import DedupReviewService
from app.services.question_dedup_service import QuestionDedupService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_context(db: Session):
    role = Role(code="reviewer", name="Reviewer")
    reviewer = User(
        username="reviewer",
        email="reviewer@example.com",
        password_hash="plain",
        role=role,
    )
    subject = Subject(code="math", name="数学")
    grade = Grade(grade_index=8, grade_code="grade_8", grade_name="八年级", edu_stage="junior")
    question_type = QuestionType(code="select_single", name="单选题", base_type_index=1)
    data_source = DataSource(code="dataset2_question_json", name="Dataset2", source_type="json")
    batch = ImportBatch(
        data_source=data_source,
        batch_no="imp_test_review_001",
        file_name="sample.json",
        import_status="SUCCESS",
    )
    db.add_all([reviewer, subject, grade, question_type, data_source, batch])
    db.commit()
    return {
        "reviewer": reviewer,
        "subject": subject,
        "grade": grade,
        "question_type": question_type,
        "data_source": data_source,
        "batch": batch,
    }


def _seed_candidate_question(db: Session, ctx, *, external_id: str = "EXISTING_001"):
    question = Question(
        subject_id=ctx["subject"].id,
        grade_id=ctx["grade"].id,
        question_type_id=ctx["question_type"].id,
    )
    db.add(question)
    db.flush()
    db.add(
        QuestionContent(
            question_id=question.id,
            stem_text="已知一次函数 y=2x+3，当 x=1 时求函数值。",
            answer_text="5",
        )
    )
    db.add(
        QuestionExternalRef(
            question_id=question.id,
            data_source_id=ctx["data_source"].id,
            external_question_id=external_id,
            is_primary=True,
        )
    )
    db.commit()
    QuestionDedupService(db).sync_question_feature(question)
    db.commit()
    return question


def _seed_pending_candidate(db: Session, ctx, candidate_question: Question, *, source_key: str):
    source_record = SourceQuestionRecord(
        import_batch_id=ctx["batch"].id,
        data_source_id=ctx["data_source"].id,
        source_record_key=source_key,
        record_type="question",
        raw_payload={
            "exerciseID": source_key,
            "subjectCategory": "math",
            "gradeIndex": 8,
            "exerciseType": "select_single",
            "question": "已知一次函数 y=2x+3，当 x=1 时求函数值。",
            "queAns": "5",
        },
        normalized_hash="hash_pending",
        parse_status="PENDING_REVIEW",
    )
    db.add(source_record)
    db.flush()
    candidate = QuestionDuplicateCandidate(
        source_record_id=source_record.id,
        candidate_question_id=candidate_question.id,
        match_type="RULE_CANDIDATE",
        confidence_score=0.99,
        comparison_snapshot={"stem_similarity": 0.99, "answer_exact": True},
    )
    db.add(candidate)
    db.commit()
    return source_record, candidate


def test_approve_duplicate_candidate_attaches_existing_question() -> None:
    db = _build_session()
    ctx = _seed_context(db)
    candidate_question = _seed_candidate_question(db, ctx)
    source_record, candidate = _seed_pending_candidate(db, ctx, candidate_question, source_key="PENDING_001")

    result = DedupReviewService(db).approve_duplicate(
        candidate_id=candidate.id,
        reviewed_by_user_id=ctx["reviewer"].id,
    )
    db.refresh(source_record)
    db.refresh(candidate)

    assert result.normalized_question_id == candidate_question.id
    assert source_record.normalized_question_id == candidate_question.id
    assert source_record.parse_status == "MATCHED_BY_REVIEW"
    assert candidate.review_status == "APPROVED"


def test_reject_duplicate_candidate_creates_new_question() -> None:
    db = _build_session()
    ctx = _seed_context(db)
    candidate_question = _seed_candidate_question(db, ctx, external_id="EXISTING_002")
    source_record, candidate = _seed_pending_candidate(db, ctx, candidate_question, source_key="PENDING_002")

    result = DedupReviewService(db).reject_duplicate(
        candidate_id=candidate.id,
        reviewed_by_user_id=ctx["reviewer"].id,
    )
    db.refresh(source_record)
    db.refresh(candidate)

    assert result.normalized_question_id != candidate_question.id
    assert source_record.normalized_question_id == result.normalized_question_id
    assert source_record.parse_status == "CREATED_BY_REVIEW"
    assert candidate.review_status == "REJECTED"
    created_question = db.scalar(select(Question).where(Question.id == result.normalized_question_id))
    assert created_question is not None
