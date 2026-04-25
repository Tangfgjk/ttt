from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.auth import Role, User
from app.models.dictionary import Grade, QuestionType, Subject
from app.models.imports import DataSource, ImportBatch, SourceQuestionRecord
from app.models.question import Question, QuestionContent, QuestionExternalRef
from app.services.question_dedup_service import DedupInput, QuestionDedupService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_basic_context(db: Session) -> dict[str, int]:
    subject = Subject(code="math", name="数学")
    grade = Grade(grade_index=7, grade_code="G7", grade_name="七年级")
    question_type = QuestionType(code="single_choice", name="单选题")
    data_source = DataSource(code="dataset2_question_json", name="Dataset2", source_type="json")
    role = Role(code="admin", name="管理员")
    user = User(
        username="reviewer",
        email="reviewer@example.com",
        password_hash="hashed",
        role=role,
    )
    batch = ImportBatch(
        data_source=data_source,
        batch_no="imp_test_001",
        file_name="sample.json",
        import_status="SUCCESS",
    )
    source_record = SourceQuestionRecord(
        import_batch=batch,
        data_source=data_source,
        source_record_key="SRC_001",
        record_type="question",
        raw_payload={"exerciseID": "SRC_001"},
        parse_status="RAW_IMPORTED",
    )
    db.add_all([subject, grade, question_type, data_source, role, user, batch, source_record])
    db.commit()
    return {
        "subject_id": subject.id,
        "grade_id": grade.id,
        "question_type_id": question_type.id,
        "data_source_id": data_source.id,
        "source_record_id": source_record.id,
    }


def _seed_question(
    db: Session,
    *,
    subject_id: int,
    grade_id: int,
    question_type_id: int,
    data_source_id: int,
    external_question_id: str = "Q_EXISTING_001",
    stem_text: str = "如图，求三角形 ABC 的面积。",
    answer_text: str = "12",
) -> Question:
    question = Question(
        subject_id=subject_id,
        grade_id=grade_id,
        question_type_id=question_type_id,
    )
    db.add(question)
    db.flush()
    db.add(
        QuestionContent(
            question_id=question.id,
            stem_text=stem_text,
            answer_text=answer_text,
        )
    )
    db.add(
        QuestionExternalRef(
            question_id=question.id,
            data_source_id=data_source_id,
            external_question_id=external_question_id,
            is_primary=True,
        )
    )
    db.commit()
    return question


def test_match_by_external_ref() -> None:
    db = _build_session()
    ids = _seed_basic_context(db)
    question = _seed_question(
        db,
        subject_id=ids["subject_id"],
        grade_id=ids["grade_id"],
        question_type_id=ids["question_type_id"],
        data_source_id=ids["data_source_id"],
    )
    service = QuestionDedupService(db)

    decision = service.evaluate(
        DedupInput(
            subject_id=ids["subject_id"],
            grade_id=ids["grade_id"],
            question_type_id=ids["question_type_id"],
            stem_text="不同题干也没关系",
            answer_text="不同答案",
            data_source_id=ids["data_source_id"],
            external_question_id="Q_EXISTING_001",
        )
    )

    assert decision.status == "MATCHED_BY_EXTERNAL_ID"
    assert decision.question_id == question.id


def test_match_by_content_hash_after_syncing_feature() -> None:
    db = _build_session()
    ids = _seed_basic_context(db)
    question = _seed_question(
        db,
        subject_id=ids["subject_id"],
        grade_id=ids["grade_id"],
        question_type_id=ids["question_type_id"],
        data_source_id=ids["data_source_id"],
    )
    service = QuestionDedupService(db)
    service.sync_question_feature(question)
    db.commit()

    decision = service.evaluate(
        DedupInput(
            subject_id=ids["subject_id"],
            grade_id=ids["grade_id"],
            question_type_id=ids["question_type_id"],
            stem_text="<p>如图，求三角形 ABC 的面积。</p>",
            answer_text="12",
        )
    )

    assert decision.status == "MATCHED_BY_CONTENT_HASH"
    assert decision.question_id == question.id


def test_create_pending_review_candidate() -> None:
    db = _build_session()
    ids = _seed_basic_context(db)
    question = _seed_question(
        db,
        subject_id=ids["subject_id"],
        grade_id=ids["grade_id"],
        question_type_id=ids["question_type_id"],
        data_source_id=ids["data_source_id"],
        stem_text=(
            "已知一次函数 y=2x+3，当自变量 x=1 时，求对应的函数值，"
            "并写出完整的计算过程、关键步骤和最终计算结果。"
        ),
        answer_text="5",
    )
    service = QuestionDedupService(db)
    service.sync_question_feature(question)
    db.commit()

    decision = service.evaluate(
        DedupInput(
            subject_id=ids["subject_id"],
            grade_id=ids["grade_id"],
            question_type_id=ids["question_type_id"],
            stem_text=(
                "已知一次函数 y=2x+3，当自变量 x=1 时，请求出对应的函数值，"
                "并写出完整的计算过程、关键步骤和最终计算结果。"
            ),
            answer_text="5",
            source_record_id=ids["source_record_id"],
        )
    )
    db.commit()

    assert decision.status == "PENDING_REVIEW"
    assert len(decision.candidates) == 1
    assert decision.candidates[0].question_id == question.id
