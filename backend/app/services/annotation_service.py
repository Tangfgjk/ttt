from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    Annotation,
    AnnotationCompetency,
    AnnotationTask,
    CoresetExperiment,
    QuestionAggregateCompetency,
    QuestionEmbedding,
    QuestionLabelAggregate,
    RecommendationBatch,
    RecommendationItem,
    ReviewTask,
)
from app.models.auth import User
from app.models.dictionary import Competency
from app.models.question import Question, QuestionContent
from app.schemas.annotations import (
    AdminSelectionRequest,
    AdminSelectionResponse,
    AnnotationCompetencyInput,
    ClaimAnnotationRequest,
    ClaimAnnotationResponse,
    PoolSummaryItem,
    PoolSummaryResponse,
    SubmitAnnotationRequest,
    SubmitAnnotationResponse,
)
from app.services.coreset_selection import CoresetCandidate, CoresetSelector

QUESTION_STATUS_PENDING = "PENDING"
QUESTION_STATUS_WAITING = "WAITING"
QUESTION_STATUS_IN_PROGRESS = "IN_PROGRESS"
QUESTION_STATUS_REVIEW_PENDING = "REVIEW_PENDING"
QUESTION_STATUS_COMPLETED = "COMPLETED"

TASK_STATUS_IN_PROGRESS = "IN_PROGRESS"
TASK_STATUS_SUBMITTED = "SUBMITTED"

ANNOTATION_STATUS_SUBMITTED = "SUBMITTED"

REVIEW_STATUS_PENDING = "PENDING"

EXPENSIVE_SELECTION_LIMIT = 600
DEFAULT_SELECTION_LIMIT = 2000


SELECTION_STRATEGIES = [
    {
        "code": "moe",
        "name": "MoE 融合策略",
        "description": "参考 Strategies.py，先取代表性样本，再用 Graph Cut 拉开差异。",
    },
    {
        "code": "kmeans",
        "name": "K-Means 覆盖",
        "description": "按文本/向量聚类，挑选最靠近各簇中心的题。",
    },
    {
        "code": "facility_location",
        "name": "Facility Location",
        "description": "最大化待选题对未标注池的覆盖增益。",
    },
    {
        "code": "graph_cut",
        "name": "Graph Cut",
        "description": "优先选择代表性强且与已选集合冗余低的题。",
    },
    {
        "code": "random",
        "name": "随机抽样",
        "description": "作为 baseline 使用，快速随机抽取题目。",
    },
]


class AnnotationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.selector = CoresetSelector()

    def pool_summary(self) -> PoolSummaryResponse:
        rows = self.db.execute(
            select(Question.annotation_status, func.count(Question.id))
            .where(Question.source_status == "ACTIVE")
            .group_by(Question.annotation_status)
        ).all()
        counts = {status_code: count for status_code, count in rows}
        statuses = [
            QUESTION_STATUS_PENDING,
            QUESTION_STATUS_WAITING,
            QUESTION_STATUS_IN_PROGRESS,
            QUESTION_STATUS_REVIEW_PENDING,
            QUESTION_STATUS_COMPLETED,
        ]
        return PoolSummaryResponse(
            items=[
                PoolSummaryItem(status=status_code, count=int(counts.get(status_code, 0)))
                for status_code in statuses
            ]
        )

    def select_questions(self, payload: AdminSelectionRequest) -> AdminSelectionResponse:
        self._ensure_user_exists(payload.triggered_by_user_id, required=False)

        candidates = self._load_unlabeled_candidates(payload.strategy)
        selections = self.selector.select(candidates, payload.strategy, payload.count)
        selected_ids = [item.question_id for item in selections]

        batch = RecommendationBatch(
            batch_no=f"rec_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            algorithm_code=payload.strategy,
            triggered_by_user_id=payload.triggered_by_user_id,
            target_stage="annotation_pool",
            context_json={
                "requested_count": payload.count,
                "candidate_count": len(candidates),
                "status_from": QUESTION_STATUS_PENDING,
                "status_to": QUESTION_STATUS_WAITING,
            },
        )
        self.db.add(batch)
        self.db.flush()

        for item in selections:
            self.db.add(
                RecommendationItem(
                    batch_id=batch.id,
                    question_id=item.question_id,
                    score=Decimal(str(item.score)),
                    rank_no=item.rank_no,
                    is_accepted=True,
                )
            )

        moved_count = 0
        if selected_ids:
            questions = list(
                self.db.scalars(
                    select(Question)
                    .where(Question.id.in_(selected_ids))
                    .where(Question.annotation_status == QUESTION_STATUS_PENDING)
                    .with_for_update()
                )
            )
            for question in questions:
                question.annotation_status = QUESTION_STATUS_WAITING
                moved_count += 1

        self.db.add(
            CoresetExperiment(
                batch_id=batch.id,
                algorithm_code=payload.strategy,
                params_json={"count": payload.count},
                metrics_json={
                    "candidate_count": len(candidates),
                    "selected_count": len(selections),
                    "moved_count": moved_count,
                },
                selected_question_count=len(selections),
            )
        )
        self.db.commit()

        return AdminSelectionResponse(
            batch_id=batch.id,
            batch_no=batch.batch_no,
            strategy=payload.strategy,
            requested_count=payload.count,
            selected_count=len(selections),
            moved_count=moved_count,
            candidate_count=len(candidates),
            question_ids=selected_ids,
        )

    def claim_questions(self, payload: ClaimAnnotationRequest) -> ClaimAnnotationResponse:
        self._ensure_user_exists(payload.annotator_user_id)

        questions = list(
            self.db.scalars(
                select(Question)
                .options(
                    selectinload(Question.subject),
                    selectinload(Question.grade),
                    selectinload(Question.question_type),
                    selectinload(Question.content),
                )
                .where(Question.source_status == "ACTIVE")
                .where(Question.annotation_status == QUESTION_STATUS_WAITING)
                .where(Question.annotation_count < Question.required_annotations)
                .where(~self._user_has_submitted_annotation(payload.annotator_user_id))
                .order_by(Question.updated_at.asc(), Question.id.asc())
                .limit(payload.count)
                .with_for_update(skip_locked=True)
            ).unique()
        )

        if len(questions) < min(10, payload.count):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="待标注池可领取题目不足 10 道，请先让管理员补充待标注池。",
            )

        tasks: list[AnnotationTask] = []
        now = datetime.utcnow()
        for question in questions:
            question.annotation_status = QUESTION_STATUS_IN_PROGRESS
            task = AnnotationTask(
                question_id=question.id,
                assignee_id=payload.annotator_user_id,
                source_batch_id=self._latest_source_batch_id(question.id),
                task_status=TASK_STATUS_IN_PROGRESS,
                assigned_at=now,
                started_at=now,
            )
            self.db.add(task)
            tasks.append(task)

        self.db.commit()
        for task in tasks:
            self.db.refresh(task)

        return ClaimAnnotationResponse(
            claimed_count=len(tasks),
            task_ids=[task.id for task in tasks],
            items=tasks,
        )

    def list_tasks(
        self,
        user_id: int,
        task_status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AnnotationTask], int]:
        self._ensure_user_exists(user_id)
        stmt = (
            select(AnnotationTask)
            .options(
                selectinload(AnnotationTask.question).selectinload(Question.subject),
                selectinload(AnnotationTask.question).selectinload(Question.grade),
                selectinload(AnnotationTask.question).selectinload(Question.question_type),
                selectinload(AnnotationTask.question).selectinload(Question.content),
            )
            .where(AnnotationTask.assignee_id == user_id)
        )
        if task_status:
            stmt = stmt.where(AnnotationTask.task_status == task_status)

        total_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = self.db.scalar(total_stmt) or 0
        items = list(
            self.db.scalars(
                stmt.order_by(AnnotationTask.assigned_at.desc(), AnnotationTask.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).unique()
        )
        return items, int(total)

    def submit_annotation(
        self,
        task_id: int,
        payload: SubmitAnnotationRequest,
    ) -> SubmitAnnotationResponse:
        self._ensure_user_exists(payload.annotator_user_id)
        task = self.db.scalar(
            select(AnnotationTask)
            .options(selectinload(AnnotationTask.question))
            .where(AnnotationTask.id == task_id)
            .with_for_update()
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标注任务不存在。")
        if task.assignee_id != payload.annotator_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能提交他人的标注任务。",
            )
        if task.task_status != TASK_STATUS_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该任务已提交或不可提交。",
            )
        if self._user_has_final_annotation(task.question_id, payload.annotator_user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该用户已标注过这道题。",
            )

        self._validate_competencies(payload.competencies)

        annotation = Annotation(
            question_id=task.question_id,
            user_id=payload.annotator_user_id,
            task_id=task.id,
            version_no=1,
            cognitive_level_id=payload.cognitive_level_id,
            confidence_level=payload.confidence_level,
            time_spent_seconds=payload.time_spent_seconds,
            is_final=True,
            annotation_status=ANNOTATION_STATUS_SUBMITTED,
        )
        annotation.competencies = [
            AnnotationCompetency(
                competency_id=item.competency_id,
                level_value=item.level_value,
            )
            for item in payload.competencies
        ]
        self.db.add(annotation)
        self.db.flush()

        task.task_status = TASK_STATUS_SUBMITTED
        task.submitted_at = datetime.utcnow()

        final_annotations = self._final_annotations(task.question_id)
        annotation_count = len(final_annotations)
        question = task.question
        question.annotation_count = annotation_count

        aggregate_id: int | None = None
        is_disputed = False
        if annotation_count < question.required_annotations:
            question.annotation_status = QUESTION_STATUS_WAITING
        else:
            aggregate = self._aggregate_question(question, final_annotations)
            aggregate_id = aggregate.id
            is_disputed = aggregate.is_disputed
            question.annotation_status = (
                QUESTION_STATUS_REVIEW_PENDING
                if aggregate.is_disputed
                else QUESTION_STATUS_COMPLETED
            )

        self.db.commit()
        self.db.refresh(annotation)

        return SubmitAnnotationResponse(
            annotation_id=annotation.id,
            question_id=task.question_id,
            annotation_count=question.annotation_count,
            required_annotations=question.required_annotations,
            question_status=question.annotation_status,
            aggregate_id=aggregate_id,
            is_disputed=is_disputed,
        )

    def _load_unlabeled_candidates(self, strategy: str) -> list[CoresetCandidate]:
        limit = (
            EXPENSIVE_SELECTION_LIMIT
            if strategy in {"facility_location", "graph_cut", "moe"}
            else DEFAULT_SELECTION_LIMIT
        )
        questions = list(
            self.db.scalars(
                select(Question)
                .join(QuestionContent, QuestionContent.question_id == Question.id)
                .options(selectinload(Question.content))
                .where(Question.source_status == "ACTIVE")
                .where(Question.annotation_status == QUESTION_STATUS_PENDING)
                .order_by(Question.id.asc())
                .limit(limit)
            ).unique()
        )
        embeddings = self._embedding_map([question.id for question in questions])
        return [
            CoresetCandidate(
                question_id=question.id,
                text=question.content.stem_text if question.content else "",
                embedding=embeddings.get(question.id),
            )
            for question in questions
        ]

    def _embedding_map(self, question_ids: list[int]) -> dict[int, list[float]]:
        if not question_ids:
            return {}
        rows = self.db.scalars(
            select(QuestionEmbedding)
            .where(QuestionEmbedding.question_id.in_(question_ids))
            .order_by(QuestionEmbedding.question_id.asc(), QuestionEmbedding.computed_at.desc())
        )
        result: dict[int, list[float]] = {}
        for row in rows:
            result.setdefault(row.question_id, row.vector_json)
        return result

    def _user_has_submitted_annotation(self, user_id: int):
        return (
            select(Annotation.id)
            .where(Annotation.question_id == Question.id)
            .where(Annotation.user_id == user_id)
            .where(Annotation.is_final.is_(True))
            .exists()
        )

    def _user_has_final_annotation(self, question_id: int, user_id: int) -> bool:
        return (
            self.db.scalar(
                select(func.count(Annotation.id))
                .where(Annotation.question_id == question_id)
                .where(Annotation.user_id == user_id)
                .where(Annotation.is_final.is_(True))
            )
            or 0
        ) > 0

    def _latest_source_batch_id(self, question_id: int) -> int | None:
        return self.db.scalar(
            select(RecommendationItem.batch_id)
            .where(RecommendationItem.question_id == question_id)
            .order_by(RecommendationItem.created_at.desc(), RecommendationItem.id.desc())
            .limit(1)
        )

    def _final_annotations(self, question_id: int) -> list[Annotation]:
        return list(
            self.db.scalars(
                select(Annotation)
                .options(selectinload(Annotation.competencies))
                .where(Annotation.question_id == question_id)
                .where(Annotation.is_final.is_(True))
                .where(Annotation.annotation_status == ANNOTATION_STATUS_SUBMITTED)
                .order_by(Annotation.created_at.asc(), Annotation.id.asc())
            ).unique()
        )

    def _aggregate_question(
        self,
        question: Question,
        annotations: list[Annotation],
    ) -> QuestionLabelAggregate:
        cognitive_ids = [annotation.cognitive_level_id for annotation in annotations]
        final_cognitive_id, cognitive_agreement = self._majority(cognitive_ids)

        aggregate = self.db.scalar(
            select(QuestionLabelAggregate).where(QuestionLabelAggregate.question_id == question.id)
        )
        if aggregate is None:
            aggregate = QuestionLabelAggregate(question_id=question.id)
            self.db.add(aggregate)
            self.db.flush()
        else:
            self.db.execute(
                delete(QuestionAggregateCompetency).where(
                    QuestionAggregateCompetency.aggregate_id == aggregate.id
                )
            )

        competency_values: dict[int, list[int]] = defaultdict(list)
        for annotation in annotations:
            for item in annotation.competencies:
                competency_values[item.competency_id].append(item.level_value)

        competency_agreements: list[float] = []
        competency_disputed = False
        for competency_id, values in competency_values.items():
            level_value, agreement = self._majority(values)
            competency_agreements.append(agreement)
            if agreement < 1:
                competency_disputed = True
            self.db.add(
                QuestionAggregateCompetency(
                    aggregate_id=aggregate.id,
                    competency_id=competency_id,
                    level_value=int(level_value or 0),
                    agreement_score=Decimal(f"{agreement:.2f}"),
                )
            )

        scores = [cognitive_agreement, *competency_agreements]
        agreement_score = sum(scores) / len(scores) if scores else 0
        aggregate.final_cognitive_level_id = final_cognitive_id
        aggregate.completed_annotation_count = len(annotations)
        aggregate.agreement_score = Decimal(f"{agreement_score:.2f}")
        aggregate.is_disputed = cognitive_agreement < 1 or competency_disputed
        aggregate.finalized_at = datetime.utcnow()
        self.db.flush()

        if aggregate.is_disputed:
            existing_review = self.db.scalar(
                select(ReviewTask)
                .where(ReviewTask.aggregate_id == aggregate.id)
                .where(ReviewTask.review_status == REVIEW_STATUS_PENDING)
            )
            if existing_review is None:
                self.db.add(
                    ReviewTask(
                        question_id=question.id,
                        aggregate_id=aggregate.id,
                        review_status=REVIEW_STATUS_PENDING,
                    )
                )
        return aggregate

    def _majority(self, values: list[int | None]) -> tuple[int | None, float]:
        if not values:
            return None, 0.0
        counter = Counter(values)
        value, count = counter.most_common(1)[0]
        return value, count / len(values)

    def _validate_competencies(self, competencies: list[AnnotationCompetencyInput]) -> None:
        ids = [item.competency_id for item in competencies]
        if len(ids) != len(set(ids)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="核心素养不能重复。",
            )
        if not ids:
            return
        existing_count = (
            self.db.scalar(select(func.count(Competency.id)).where(Competency.id.in_(ids))) or 0
        )
        if existing_count != len(ids):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="存在无效的核心素养。",
            )

    def _ensure_user_exists(self, user_id: int | None, *, required: bool = True) -> None:
        if user_id is None and not required:
            return
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="缺少用户 ID。",
            )
        exists = self.db.scalar(select(User.id).where(User.id == user_id))
        if exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在。")
