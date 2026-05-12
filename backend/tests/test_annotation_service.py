from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.assessment import AnnotationReviewLog, AnnotationTask, QuestionLabelAggregate, ReviewTask
from app.models.auth import Role, User
from app.models.dictionary import Competency, Grade, Subject
from app.models.question import Question, QuestionContent
from app.schemas.annotations import (
    AdminReviewDecisionRequest,
    AdminSelectionRequest,
    ClaimAnnotationRequest,
    ClaimReviewTaskRequest,
    SubmitAnnotationRequest,
    SubmitReviewTaskRequest,
)
from app.services.annotation_service import AnnotationService


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_role(db: Session, code: str, name: str) -> Role:
    role = Role(code=code, name=name)
    db.add(role)
    db.flush()
    return role


def _seed_user(
    db: Session,
    *,
    role: Role,
    username: str,
    training_scope: str = "junior",
) -> User:
    user = User(
        username=username,
        email=f"{username}@ttt.local",
        password_hash="plain",
        role_id=role.id,
        real_name=username,
        is_verified=True,
        training_scope=training_scope,
    )
    db.add(user)
    db.flush()
    return user


def _seed_subject_and_grade(db: Session) -> tuple[Subject, Grade]:
    subject = Subject(code="math", name="数学")
    grade = Grade(
        grade_index=8,
        grade_code="grade_8",
        grade_name="八年级",
        edu_stage="junior",
    )
    db.add_all([subject, grade])
    db.flush()
    return subject, grade


def _seed_waiting_questions(db: Session, *, total: int) -> list[Question]:
    subject, grade = _seed_subject_and_grade(db)
    items: list[Question] = []
    for index in range(total):
        question = Question(
            subject_id=subject.id,
            grade_id=grade.id,
            annotation_status="WAITING",
            source_status="ACTIVE",
            required_annotations=3,
            annotation_count=0,
        )
        db.add(question)
        db.flush()
        db.add(QuestionContent(question_id=question.id, stem_text=f"待标注题目 {index + 1}"))
        items.append(question)
    db.commit()
    return items


def _seed_pending_questions(db: Session, *, total: int) -> list[Question]:
    subject, grade = _seed_subject_and_grade(db)
    items: list[Question] = []
    for index in range(total):
        question = Question(
            subject_id=subject.id,
            grade_id=grade.id,
            annotation_status="PENDING",
            source_status="ACTIVE",
            required_annotations=3,
            annotation_count=0,
        )
        db.add(question)
        db.flush()
        db.add(QuestionContent(question_id=question.id, stem_text=f"链爣娉ㄩ鐩?{index + 1}"))
        items.append(question)
    db.commit()
    return items


def _seed_competencies(db: Session) -> list[Competency]:
    items = [
        Competency(code="reasoning", name="推理能力", display_order=1),
        Competency(code="modeling", name="建模能力", display_order=2),
    ]
    db.add_all(items)
    db.commit()
    return items


def _seed_manual_tasks(
    db: Session,
    *,
    annotators: list[User],
) -> tuple[Question, list[Competency], list[AnnotationTask]]:
    subject, grade = _seed_subject_and_grade(db)
    competencies = _seed_competencies(db)
    question = Question(
        subject_id=subject.id,
        grade_id=grade.id,
        annotation_status="IN_PROGRESS",
        source_status="ACTIVE",
        required_annotations=3,
        annotation_count=0,
    )
    db.add(question)
    db.flush()
    db.add(QuestionContent(question_id=question.id, stem_text="并行标注测试题"))
    tasks: list[AnnotationTask] = []
    for annotator in annotators:
        task = AnnotationTask(
            question_id=question.id,
            assignee_id=annotator.id,
            task_status="IN_PROGRESS",
        )
        db.add(task)
        tasks.append(task)
    db.commit()
    return question, competencies, tasks


def test_parallel_claim_allows_multiple_annotators_to_claim_same_questions() -> None:
    db = _build_session()
    annotator_role = _seed_role(db, "annotator", "标注员")
    annotator_a = _seed_user(db, role=annotator_role, username="annotator_a")
    annotator_b = _seed_user(db, role=annotator_role, username="annotator_b")
    _seed_waiting_questions(db, total=10)

    service = AnnotationService(db)
    first_claim = service.claim_questions(
        ClaimAnnotationRequest(annotator_user_id=annotator_a.id, count=10)
    )
    second_claim = service.claim_questions(
        ClaimAnnotationRequest(annotator_user_id=annotator_b.id, count=10)
    )

    assert first_claim.claimed_count == 10
    assert second_claim.claimed_count == 10
    assert {item.question_id for item in first_claim.items} == {
        item.question_id for item in second_claim.items
    }
    assert all(item.progress.required_annotations == 3 for item in second_claim.items)
    assert all(item.progress.active_annotation_count == 2 for item in second_claim.items)


def test_admin_selection_returns_batch_and_waiting_questions() -> None:
    db = _build_session()
    admin_role = _seed_role(db, "admin", "绠＄悊鍛?")
    admin = _seed_user(db, role=admin_role, username="admin_select", training_scope="none")
    _seed_pending_questions(db, total=300)

    service = AnnotationService(db)
    result = service.select_questions(
        AdminSelectionRequest(
            strategy="kmeans",
            count=10,
            data_scope="pending",
            triggered_by_user_id=admin.id,
        )
    )

    waiting_count = db.scalar(
        select(func.count()).select_from(Question).where(Question.annotation_status == "WAITING")
    )

    assert result.selected_count == 10
    assert result.moved_count == 10
    assert len(result.question_ids) == 10
    assert len(result.moved_question_ids) == 10
    assert waiting_count == 10


def test_three_annotators_with_majority_consensus_complete_question() -> None:
    db = _build_session()
    annotator_role = _seed_role(db, "annotator", "标注员")
    annotators = [
        _seed_user(db, role=annotator_role, username="annotator_1"),
        _seed_user(db, role=annotator_role, username="annotator_2"),
        _seed_user(db, role=annotator_role, username="annotator_3"),
    ]
    question, competencies, tasks = _seed_manual_tasks(db, annotators=annotators)
    service = AnnotationService(db)

    payloads = [
        SubmitAnnotationRequest(
            annotator_user_id=annotators[0].id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 2},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotators[1].id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 2},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotators[2].id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 3},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
    ]

    for task, payload in zip(tasks, payloads):
        result = service.submit_annotation(task.id, payload)

    db.refresh(question)
    aggregate = db.scalar(
        select(QuestionLabelAggregate).where(QuestionLabelAggregate.question_id == question.id)
    )
    logs = list(
        db.scalars(select(AnnotationReviewLog).where(AnnotationReviewLog.question_id == question.id))
    )

    assert result.is_disputed is False
    assert question.annotation_status == "COMPLETED"
    assert question.annotation_count == 3
    assert aggregate is not None
    assert aggregate.is_disputed is False
    assert any(log.action_code == "AUTO_CONSENSUS_COMPLETED" for log in logs)


def test_admin_can_view_disputed_question_and_reject_for_additional_annotations() -> None:
    db = _build_session()
    annotator_role = _seed_role(db, "annotator", "标注员")
    admin_role = _seed_role(db, "admin", "管理员")
    annotators = [
        _seed_user(db, role=annotator_role, username="annotator_x1"),
        _seed_user(db, role=annotator_role, username="annotator_x2"),
        _seed_user(db, role=annotator_role, username="annotator_x3"),
    ]
    admin = _seed_user(db, role=admin_role, username="admin_user", training_scope="none")
    question, competencies, tasks = _seed_manual_tasks(db, annotators=annotators)
    service = AnnotationService(db)

    payloads = [
        SubmitAnnotationRequest(
            annotator_user_id=annotators[0].id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 0},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotators[1].id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 1},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotators[2].id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 2},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
    ]

    for task, payload in zip(tasks, payloads):
        service.submit_annotation(task.id, payload)

    overview = service.get_admin_question_review(question.id, admin.id)
    reopened = service.reject_admin_question_review(
        question.id,
        AdminReviewDecisionRequest(
            admin_user_id=admin.id,
            review_comment="三人意见分散，补充第 4 票。",
            additional_annotations=1,
        ),
    )

    db.refresh(question)
    review_task = db.scalar(select(ReviewTask).where(ReviewTask.question_id == question.id))
    logs = list(
        db.scalars(select(AnnotationReviewLog).where(AnnotationReviewLog.question_id == question.id))
    )

    assert overview.consensus.consensus_status == "DISPUTED"
    assert len(overview.annotations) == 3
    assert question.annotation_status == "WAITING"
    assert question.required_annotations == 4
    assert reopened.remaining_annotation_count == 1
    assert review_task is not None
    assert review_task.review_status == "COMPLETED"
    assert any(log.action_code == "ADMIN_REJECTED_FOR_REANNOTATION" for log in logs)
    assert any(log.action_code == "AUTO_REVIEW_CREATED" for log in logs)


def test_reopened_questions_prioritize_new_annotators_for_additional_votes() -> None:
    db = _build_session()
    annotator_role = _seed_role(db, "annotator", "标注员")
    annotator_a = _seed_user(db, role=annotator_role, username="annotator_a1")
    annotator_b = _seed_user(db, role=annotator_role, username="annotator_b1")
    annotator_c = _seed_user(db, role=annotator_role, username="annotator_c1")
    annotator_new = _seed_user(db, role=annotator_role, username="annotator_new")
    waiting_questions = _seed_waiting_questions(db, total=11)
    service = AnnotationService(db)
    reopened_question = waiting_questions[0]
    reopened_question.annotation_status = "WAITING"
    reopened_question.annotation_count = 3
    reopened_question.required_annotations = 4
    db.add_all(
        [
            AnnotationTask(question_id=reopened_question.id, assignee_id=annotator_a.id, task_status="SUBMITTED"),
            AnnotationTask(question_id=reopened_question.id, assignee_id=annotator_b.id, task_status="SUBMITTED"),
            AnnotationTask(question_id=reopened_question.id, assignee_id=annotator_c.id, task_status="SUBMITTED"),
        ]
    )
    db.commit()

    claim_for_new = service.claim_questions(
        ClaimAnnotationRequest(annotator_user_id=annotator_new.id, count=10)
    )
    claim_for_old = service.claim_questions(
        ClaimAnnotationRequest(annotator_user_id=annotator_a.id, count=10)
    )

    assert claim_for_new.items[0].question_id == reopened_question.id
    assert all(item.question_id != reopened_question.id for item in claim_for_old.items)


def test_annotator_history_returns_review_and_adoption_status() -> None:
    db = _build_session()
    annotator_role = _seed_role(db, "annotator", "标注员")
    reviewer_role = _seed_role(db, "reviewer", "复核员")
    annotator = _seed_user(db, role=annotator_role, username="annotator_hist")
    annotator_b = _seed_user(db, role=annotator_role, username="annotator_hist_b")
    annotator_c = _seed_user(db, role=annotator_role, username="annotator_hist_c")
    reviewer = _seed_user(db, role=reviewer_role, username="reviewer_hist", training_scope="none")
    question, competencies, tasks = _seed_manual_tasks(
        db,
        annotators=[annotator, annotator_b, annotator_c],
    )
    service = AnnotationService(db)

    payloads = [
        SubmitAnnotationRequest(
            annotator_user_id=annotator.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 0},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotator_b.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 1},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotator_c.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 2},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
    ]
    for task, payload in zip(tasks, payloads):
        service.submit_annotation(task.id, payload)

    review_claim = service.claim_review_tasks(
        ClaimReviewTaskRequest(reviewer_user_id=reviewer.id, count=1)
    )
    service.submit_review_task(
        review_claim.items[0].id,
        SubmitReviewTaskRequest(
            reviewer_user_id=reviewer.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 1},
            ],
            review_comment="采用 1 级作为最终结论。",
        ),
    )

    history, total = service.list_annotator_history(annotator.id, page=1, page_size=20)

    assert total == 1
    assert history[0].review_state == "COMPLETED"
    assert history[0].adoption_status == "OVERRIDDEN"
    assert history[0].final_aggregate is not None


def test_workspace_summary_counts_for_annotator_and_reviewer() -> None:
    db = _build_session()
    annotator_role = _seed_role(db, "annotator", "标注员")
    reviewer_role = _seed_role(db, "reviewer", "复核员")
    annotator = _seed_user(db, role=annotator_role, username="annotator_summary")
    annotator_b = _seed_user(db, role=annotator_role, username="annotator_summary_b")
    annotator_c = _seed_user(db, role=annotator_role, username="annotator_summary_c")
    reviewer = _seed_user(db, role=reviewer_role, username="reviewer_summary", training_scope="none")
    question, competencies, tasks = _seed_manual_tasks(
        db,
        annotators=[annotator, annotator_b, annotator_c],
    )
    service = AnnotationService(db)

    annotator_summary_before = service.get_workspace_summary(annotator.id)
    assert annotator_summary_before.pending_task_count == 1

    payloads = [
        SubmitAnnotationRequest(
            annotator_user_id=annotator.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 0},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotator_b.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 1},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
        SubmitAnnotationRequest(
            annotator_user_id=annotator_c.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 2},
                {"competency_id": competencies[1].id, "level_value": 1},
            ],
        ),
    ]
    for task, payload in zip(tasks, payloads):
        service.submit_annotation(task.id, payload)

    review_claim = service.claim_review_tasks(
        ClaimReviewTaskRequest(reviewer_user_id=reviewer.id, count=1)
    )
    service.submit_review_task(
        review_claim.items[0].id,
        SubmitReviewTaskRequest(
            reviewer_user_id=reviewer.id,
            competencies=[
                {"competency_id": competencies[0].id, "level_value": 1},
            ],
            review_comment="完成复核。",
        ),
    )

    annotator_summary_after = service.get_workspace_summary(annotator.id)
    reviewer_summary_after = service.get_workspace_summary(reviewer.id)

    assert annotator_summary_after.pending_task_count == 0
    assert annotator_summary_after.completed_today_count == 1
    assert annotator_summary_after.escalated_count == 1
    assert reviewer_summary_after.pending_task_count == 0
    assert reviewer_summary_after.completed_today_count == 1
    assert reviewer_summary_after.completed_review_count == 1
