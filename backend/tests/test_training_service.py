from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.assessment import QuestionGoldCompetency, QuestionGoldLabel
from app.models.auth import Role, User
from app.models.dictionary import Competency, Grade, Subject
from app.models.question import Question, QuestionContent
from app.schemas.annotations import ClaimAnnotationRequest
from app.schemas.training import TrainingCompetencyAnswer, TrainingQuestionAnswer, TrainingSubmitRequest
from app.services.annotation_service import AnnotationService
from app.services.training_service import STAGE_COMPETENCY_CODES, TrainingService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_annotator(db: Session, *, training_scope: str = "none") -> User:
    role = Role(code="annotator", name="标注员")
    db.add(role)
    db.flush()
    user = User(
        username=f"annotator_{training_scope}",
        email=f"{training_scope}@ttt.local",
        password_hash="annotator123",
        role_id=role.id,
        real_name="测试标注员",
        is_verified=True,
        training_scope=training_scope,
    )
    db.add(user)
    db.flush()
    return user


def _seed_stage_gold_labels(db: Session, stage: str) -> tuple[User, list[Competency]]:
    user = _seed_annotator(db)
    subject = Subject(code="math", name="数学")
    grade = Grade(grade_index=10 if stage == "senior" else 8, grade_code=f"{stage}_grade", grade_name="测试年级", edu_stage=stage)
    db.add_all([subject, grade])
    db.flush()

    competencies: list[Competency] = []
    for index, code in enumerate(STAGE_COMPETENCY_CODES[stage], start=1):
        competency = Competency(code=code, name=code, display_order=index)
        db.add(competency)
        competencies.append(competency)
    db.flush()

    for index, competency in enumerate(competencies, start=1):
        question = Question(
            subject_id=subject.id,
            grade_id=grade.id,
            annotation_status="PENDING",
            source_status="ACTIVE",
        )
        db.add(question)
        db.flush()
        db.add(QuestionContent(question_id=question.id, stem_text=f"{stage} 训练题 {index}"))
        db.flush()
        gold = QuestionGoldLabel(question_id=question.id, label_source="test")
        db.add(gold)
        db.flush()
        db.add(
            QuestionGoldCompetency(
                gold_label_id=gold.id,
                competency_id=competency.id,
                level_value=1,
            )
        )
    db.commit()
    return user, competencies


def test_training_submit_updates_user_scope_when_answers_match_gold() -> None:
    db = _build_session()
    user, competencies = _seed_stage_gold_labels(db, "senior")
    service = TrainingService(db)
    module = service.get_module(user.id, "senior")

    result = service.submit_training(
        TrainingSubmitRequest(
            user_id=user.id,
            stage="senior",
            answers=[
                TrainingQuestionAnswer(
                    question_id=question.question_id,
                    competencies=[
                        TrainingCompetencyAnswer(
                            competency_id=competencies[index].id,
                            level_value=1,
                        )
                    ],
                )
                for index, question in enumerate(module.questions)
            ],
        )
    )

    db.refresh(user)
    assert result.passed is True
    assert result.training_scope == "senior"
    assert user.training_scope == "senior"


def test_training_module_includes_guide_examples_and_question_fields() -> None:
    db = _build_session()
    user, _competencies = _seed_stage_gold_labels(db, "junior")
    service = TrainingService(db)

    module = service.get_module(user.id, "junior")

    assert module.questions
    assert module.guide_examples
    assert len(module.guide_examples) <= 2
    assert module.guide_examples[0].competencies
    assert module.guide_examples[0].coach_tip


def test_claim_questions_rejects_untrained_annotator() -> None:
    db = _build_session()
    user = _seed_annotator(db, training_scope="none")
    subject = Subject(code="math2", name="数学")
    grade = Grade(grade_index=8, grade_code="grade_8", grade_name="八年级", edu_stage="junior")
    db.add_all([subject, grade])
    db.flush()
    for index in range(10):
        question = Question(
            subject_id=subject.id,
            grade_id=grade.id,
            annotation_status="WAITING",
            source_status="ACTIVE",
        )
        db.add(question)
        db.flush()
        db.add(QuestionContent(question_id=question.id, stem_text=f"待领取标注题 {index + 1}"))
    db.commit()

    service = AnnotationService(db)
    try:
        service.claim_questions(ClaimAnnotationRequest(annotator_user_id=user.id, count=10))
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Expected untrained annotator to be blocked.")
