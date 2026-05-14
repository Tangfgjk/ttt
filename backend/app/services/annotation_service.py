from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import random
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    Annotation,
    AnnotationCompetency,
    AnnotationReviewLog,
    AnnotationTask,
    CoresetExperiment,
    QuestionAggregateCompetency,
    QuestionEmbedding,
    QuestionGoldCompetency,
    QuestionGoldLabel,
    QuestionLabelAggregate,
    RecommendationBatch,
    RecommendationItem,
    ReviewTask,
)
from app.models.auth import User
from app.models.dictionary import CognitiveLevel, Competency, Grade
from app.models.question import Question, QuestionContent
from app.schemas.annotations import (
    AdminAggregateOverrideRequest,
    AdminQuestionAnnotationOut,
    AdminQuestionReviewOut,
    AdminPoolResetRequest,
    AdminPoolResetResponse,
    AdminReviewDecisionRequest,
    AdminSelectionRequest,
    AdminSelectionResponse,
    AnnotatorHistoryItemOut,
    AnnotationAggregateCompetencyOut,
    AnnotationAggregateOut,
    AnnotationCompetencyInput,
    AnnotationConsensusDimensionOut,
    AnnotationConsensusSummaryOut,
    AnnotationConsensusVoteOut,
    AnnotationReviewLogOut,
    AnnotationTaskOut,
    AnnotationTaskProgressOut,
    ClaimAnnotationRequest,
    ClaimAnnotationResponse,
    ClaimReviewTaskRequest,
    ClaimReviewTaskResponse,
    PoolSummaryItem,
    PoolSummaryResponse,
    ReviewAnnotationCompetencyOut,
    ReviewAnnotationOut,
    ReviewTaskOut,
    SelectionBatchRollbackRequest,
    SelectionBatchRollbackResponse,
    SelectionBatchSummaryOut,
    SubmitAnnotationRequest,
    SubmitAnnotationResponse,
    SubmitReviewTaskRequest,
    SubmitReviewTaskResponse,
    WorkspaceSummaryOut,
)
from app.services.coreset_selection import CoresetCandidate, CoresetSelector
from app.services.training_service import training_scope_allows_stage

QUESTION_STATUS_PENDING = "PENDING"
QUESTION_STATUS_WAITING = "WAITING"
QUESTION_STATUS_IN_PROGRESS = "IN_PROGRESS"
QUESTION_STATUS_REVIEW_PENDING = "REVIEW_PENDING"
QUESTION_STATUS_COMPLETED = "COMPLETED"

TASK_STATUS_IN_PROGRESS = "IN_PROGRESS"
TASK_STATUS_SUBMITTED = "SUBMITTED"
TASK_STATUS_RECALLED = "RECALLED"

ANNOTATION_STATUS_SUBMITTED = "SUBMITTED"

REVIEW_STATUS_PENDING = "PENDING"
REVIEW_STATUS_IN_PROGRESS = "IN_PROGRESS"
REVIEW_STATUS_COMPLETED = "COMPLETED"

ACTION_LABELS = {
    "ANNOTATION_SUBMITTED": "标注员提交标注",
    "AUTO_CONSENSUS_COMPLETED": "系统自动完成多数聚合",
    "AUTO_REVIEW_CREATED": "系统创建争议复核任务",
    "REVIEW_TASK_CLAIMED": "复核员领取复核任务",
    "REVIEW_SUBMITTED": "复核员提交复核结论",
    "AUTO_REVIEW_CLOSED": "系统关闭待处理复核任务",
    "ADMIN_APPROVED": "管理员审核通过",
    "ADMIN_REJECTED_FOR_REANNOTATION": "管理员打回补标",
    "ADMIN_OVERRIDE_FINAL_RESULT": "管理员修改最终标注结果",
}

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

    def get_workspace_summary(self, user_id: int) -> WorkspaceSummaryOut:
        user = self._require_user(user_id)
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        if user.role.code == "annotator":
            pending_task_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(AnnotationTask)
                    .where(AnnotationTask.assignee_id == user.id)
                    .where(AnnotationTask.task_status == TASK_STATUS_IN_PROGRESS)
                )
                or 0
            )
            completed_today_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(Annotation)
                    .where(Annotation.user_id == user.id)
                    .where(Annotation.is_final.is_(True))
                    .where(Annotation.created_at >= start_of_day)
                )
                or 0
            )
            escalated_count = int(
                self.db.scalar(
                    select(func.count(func.distinct(Annotation.question_id)))
                    .select_from(Annotation)
                    .join(ReviewTask, ReviewTask.question_id == Annotation.question_id)
                    .where(Annotation.user_id == user.id)
                    .where(Annotation.is_final.is_(True))
                )
                or 0
            )
            return WorkspaceSummaryOut(
                user_id=user.id,
                role=user.role.code,
                pending_task_count=pending_task_count,
                completed_today_count=completed_today_count,
                escalated_count=escalated_count,
                completed_review_count=0,
            )

        if user.role.code == "reviewer":
            pending_task_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(ReviewTask)
                    .where(ReviewTask.reviewer_id == user.id)
                    .where(ReviewTask.review_status == REVIEW_STATUS_IN_PROGRESS)
                )
                or 0
            )
            completed_today_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(ReviewTask)
                    .where(ReviewTask.reviewer_id == user.id)
                    .where(ReviewTask.review_status == REVIEW_STATUS_COMPLETED)
                    .where(ReviewTask.reviewed_at >= start_of_day)
                )
                or 0
            )
            completed_review_count = int(
                self.db.scalar(
                    select(func.count())
                    .select_from(ReviewTask)
                    .where(ReviewTask.reviewer_id == user.id)
                    .where(ReviewTask.review_status == REVIEW_STATUS_COMPLETED)
                )
                or 0
            )
            return WorkspaceSummaryOut(
                user_id=user.id,
                role=user.role.code,
                pending_task_count=pending_task_count,
                completed_today_count=completed_today_count,
                escalated_count=0,
                completed_review_count=completed_review_count,
            )

        return WorkspaceSummaryOut(
            user_id=user.id,
            role=user.role.code,
            pending_task_count=0,
            completed_today_count=0,
            escalated_count=0,
            completed_review_count=0,
        )

    def select_questions(self, payload: AdminSelectionRequest) -> AdminSelectionResponse:
        self._ensure_user_exists(payload.triggered_by_user_id, required=False)

        candidate_ids = self._load_candidate_ids(payload.data_scope)
        working_limit = self.selector.working_set_size(
            payload.strategy,
            payload.count,
            len(candidate_ids),
        )
        if len(candidate_ids) > working_limit:
            sampled_ids = self._sample_candidate_ids(candidate_ids, working_limit)
        else:
            sampled_ids = candidate_ids
        candidates = self._load_candidates_by_ids(sampled_ids)
        selections = self.selector.select(candidates, payload.strategy, payload.count)
        selected_ids = [item.question_id for item in selections]

        batch = RecommendationBatch(
            batch_no=f"rec_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            algorithm_code=payload.strategy,
            triggered_by_user_id=payload.triggered_by_user_id,
            target_stage="annotation_pool",
            context_json={
                "requested_count": payload.count,
                "candidate_count": len(candidate_ids),
                "data_scope": payload.data_scope,
                "status_from": QUESTION_STATUS_PENDING if payload.data_scope == "pending" else "ALL",
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
        moved_question_ids: list[int] = []
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
                moved_question_ids.append(question.id)

        self.db.add(
            CoresetExperiment(
                batch_id=batch.id,
                algorithm_code=payload.strategy,
                params_json={"count": payload.count, "data_scope": payload.data_scope},
                metrics_json={
                    "candidate_count": len(candidates),
                    "working_candidate_count": len(candidates),
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
            candidate_count=len(candidate_ids),
            question_ids=selected_ids,
            moved_question_ids=moved_question_ids,
        )

    def list_selection_batches(self, limit: int = 20) -> list[SelectionBatchSummaryOut]:
        batches = list(
            self.db.scalars(
                select(RecommendationBatch)
                .order_by(RecommendationBatch.created_at.desc(), RecommendationBatch.id.desc())
                .limit(limit)
            )
        )
        return [self._serialize_selection_batch(batch) for batch in batches]

    def reset_annotation_pool(self, payload: AdminPoolResetRequest) -> AdminPoolResetResponse:
        self._require_admin(payload.admin_user_id)
        result = self._reset_question_pool()
        self.db.commit()
        return AdminPoolResetResponse(**result)

    def rollback_selection_batch(
        self,
        batch_id: int,
        payload: SelectionBatchRollbackRequest,
    ) -> SelectionBatchRollbackResponse:
        self._require_admin(payload.admin_user_id)
        batch = self.db.get(RecommendationBatch, batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题批次不存在。")

        question_ids = list(
            self.db.scalars(
                select(RecommendationItem.question_id).where(RecommendationItem.batch_id == batch_id)
            )
        )
        result = self._reset_question_pool(question_ids=question_ids, source_batch_id=batch_id)
        self.db.commit()
        return SelectionBatchRollbackResponse(
            batch_id=batch.id,
            batch_no=batch.batch_no,
            **result,
        )

    def claim_questions(self, payload: ClaimAnnotationRequest) -> ClaimAnnotationResponse:
        user = self._require_user(payload.annotator_user_id)
        self._require_annotator(user)
        allowed_stages = self._allowed_training_stages(user)
        active_task_count_subquery = (
            select(func.count(AnnotationTask.id))
            .where(AnnotationTask.question_id == Question.id)
            .where(AnnotationTask.task_status == TASK_STATUS_IN_PROGRESS)
            .scalar_subquery()
        )
        user_active_task_exists = (
            select(AnnotationTask.id)
            .where(AnnotationTask.question_id == Question.id)
            .where(AnnotationTask.assignee_id == payload.annotator_user_id)
            .where(AnnotationTask.task_status == TASK_STATUS_IN_PROGRESS)
            .exists()
        )
        user_historical_task_exists = (
            select(AnnotationTask.id)
            .where(AnnotationTask.question_id == Question.id)
            .where(AnnotationTask.assignee_id == payload.annotator_user_id)
            .exists()
        )
        supplement_priority = case((Question.annotation_count > 0, 0), else_=1)

        stmt = (
            select(Question)
            .join(Grade, Grade.id == Question.grade_id)
            .options(
                selectinload(Question.subject),
                selectinload(Question.grade),
                selectinload(Question.question_type),
                selectinload(Question.content),
            )
            .where(Question.source_status == "ACTIVE")
            .where(Question.annotation_status.in_([QUESTION_STATUS_WAITING, QUESTION_STATUS_IN_PROGRESS]))
            .where((Question.annotation_count + func.coalesce(active_task_count_subquery, 0)) < Question.required_annotations)
            .where(~self._user_has_submitted_annotation(payload.annotator_user_id))
            .where(~user_active_task_exists)
            .where((Question.annotation_count == 0) | (~user_historical_task_exists))
            .order_by(
                supplement_priority.asc(),
                Question.annotation_count.desc(),
                Question.updated_at.asc(),
                Question.id.asc(),
            )
            .limit(payload.count)
            .with_for_update(skip_locked=True)
        )
        if allowed_stages is not None:
            stmt = stmt.where(Grade.edu_stage.in_(allowed_stages))

        questions = list(self.db.scalars(stmt).unique())

        if not questions:
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
            items=[self._serialize_annotation_task(task) for task in tasks],
        )

    def list_tasks(
        self,
        user_id: int,
        task_status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AnnotationTaskOut], int]:
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
        return [self._serialize_annotation_task(item) for item in items], int(total)

    def list_annotator_history(
        self,
        annotator_user_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[AnnotatorHistoryItemOut], int]:
        user = self._require_user(annotator_user_id)
        self._require_annotator(user)
        stmt = (
            select(Annotation)
            .options(
                selectinload(Annotation.user),
                selectinload(Annotation.task),
                selectinload(Annotation.question).selectinload(Question.subject),
                selectinload(Annotation.question).selectinload(Question.grade),
                selectinload(Annotation.question).selectinload(Question.question_type),
                selectinload(Annotation.question).selectinload(Question.content),
                selectinload(Annotation.competencies).selectinload(
                    AnnotationCompetency.competency
                ),
            )
            .where(Annotation.user_id == annotator_user_id)
            .where(Annotation.is_final.is_(True))
        )
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        rows = list(
            self.db.scalars(
                stmt.order_by(Annotation.created_at.desc(), Annotation.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).unique()
        )
        return [self._serialize_annotator_history_item(item) for item in rows], int(total)

    def submit_annotation(
        self,
        task_id: int,
        payload: SubmitAnnotationRequest,
    ) -> SubmitAnnotationResponse:
        user = self._require_user(payload.annotator_user_id)
        self._require_annotator(user)
        task = self.db.scalar(
            select(AnnotationTask)
            .options(selectinload(AnnotationTask.question).selectinload(Question.grade))
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

        self._ensure_training_access_for_question(user, task.question)
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
        self._append_review_log(
            question_id=task.question_id,
            actor_user=user,
            action_code="ANNOTATION_SUBMITTED",
            detail_json={
                "annotation_id": annotation.id,
                "task_id": task.id,
                "confidence_level": payload.confidence_level,
            },
        )

        final_annotations = self._final_annotations(task.question_id)
        annotation_count = len(final_annotations)
        question = task.question
        question.annotation_count = annotation_count

        aggregate_id: int | None = None
        is_disputed = False
        active_task_count = self._active_task_count(task.question_id)
        if annotation_count < question.required_annotations:
            question.annotation_status = (
                QUESTION_STATUS_IN_PROGRESS if active_task_count > 0 else QUESTION_STATUS_WAITING
            )
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

    def claim_review_tasks(self, payload: ClaimReviewTaskRequest) -> ClaimReviewTaskResponse:
        reviewer = self._require_user(payload.reviewer_user_id)
        self._require_reviewer(reviewer)
        stmt = (
            select(ReviewTask)
            .join(Question, Question.id == ReviewTask.question_id)
            .where(ReviewTask.review_status == REVIEW_STATUS_PENDING)
            .where(Question.annotation_status == QUESTION_STATUS_REVIEW_PENDING)
            .order_by(ReviewTask.created_at.asc(), ReviewTask.id.asc())
            .limit(payload.count)
            .with_for_update(skip_locked=True)
        )
        tasks = list(self.db.scalars(stmt).unique())
        for task in tasks:
            task.reviewer_id = reviewer.id
            task.review_status = REVIEW_STATUS_IN_PROGRESS
            task.reviewed_at = None
            self._append_review_log(
                question_id=task.question_id,
                aggregate_id=task.aggregate_id,
                review_task_id=task.id,
                actor_user=reviewer,
                action_code="REVIEW_TASK_CLAIMED",
                detail_json={"review_task_id": task.id},
            )

        self.db.commit()
        task_ids = [task.id for task in tasks]
        return ClaimReviewTaskResponse(
            claimed_count=len(task_ids),
            task_ids=task_ids,
            items=[self._serialize_review_task(task_id) for task_id in task_ids],
        )

    def list_review_tasks(
        self,
        reviewer_user_id: int,
        review_status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ReviewTaskOut], int]:
        reviewer = self._require_user(reviewer_user_id)
        self._require_reviewer(reviewer)
        stmt = select(ReviewTask).where(ReviewTask.reviewer_id == reviewer.id)
        if review_status:
            stmt = stmt.where(ReviewTask.review_status == review_status)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(
            self.db.scalars(
                stmt.order_by(ReviewTask.created_at.desc(), ReviewTask.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return [self._serialize_review_task(task.id) for task in rows], int(total)

    def submit_review_task(
        self,
        review_task_id: int,
        payload: SubmitReviewTaskRequest,
    ) -> SubmitReviewTaskResponse:
        reviewer = self._require_user(payload.reviewer_user_id)
        self._require_reviewer(reviewer)
        self._validate_competencies(payload.competencies)

        task = self.db.scalar(
            select(ReviewTask)
            .options(
                selectinload(ReviewTask.question),
                selectinload(ReviewTask.aggregate),
            )
            .where(ReviewTask.id == review_task_id)
            .with_for_update()
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="复核任务不存在")
        if task.reviewer_id != reviewer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能提交他人的复核任务",
            )
        if task.review_status != REVIEW_STATUS_IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该复核任务不可提交")

        aggregate = task.aggregate
        aggregate.final_cognitive_level_id = (
            payload.cognitive_level_id
            if payload.cognitive_level_id is not None
            else aggregate.final_cognitive_level_id
        )
        aggregate.is_disputed = False
        aggregate.agreement_score = Decimal("1.00")
        aggregate.finalized_at = datetime.utcnow()
        existing_competency_values = {
            item.competency_id: item.level_value for item in aggregate.competencies
        }
        for item in payload.competencies:
            existing_competency_values[item.competency_id] = item.level_value
        self.db.execute(
            delete(QuestionAggregateCompetency).where(
                QuestionAggregateCompetency.aggregate_id == aggregate.id
            )
        )
        for competency_id, level_value in existing_competency_values.items():
            self.db.add(
                QuestionAggregateCompetency(
                    aggregate_id=aggregate.id,
                    competency_id=competency_id,
                    level_value=level_value,
                    agreement_score=Decimal("1.00"),
                )
            )

        task.review_status = REVIEW_STATUS_COMPLETED
        task.review_comment = payload.review_comment
        task.reviewed_at = datetime.utcnow()
        task.question.annotation_status = QUESTION_STATUS_COMPLETED
        self._close_open_review_tasks(
            task.question_id,
            exclude_review_task_id=task.id,
            review_comment=payload.review_comment or "复核完成并关闭其余待处理复核任务。",
        )
        self._append_review_log(
            question_id=task.question_id,
            aggregate_id=aggregate.id,
            review_task_id=task.id,
            actor_user=reviewer,
            action_code="REVIEW_SUBMITTED",
            comment=payload.review_comment,
            detail_json={"review_task_id": task.id},
        )
        self.db.commit()

        return SubmitReviewTaskResponse(
            review_task_id=task.id,
            question_id=task.question_id,
            aggregate_id=aggregate.id,
            review_status=task.review_status,
            question_status=task.question.annotation_status,
        )

    def get_admin_question_review(
        self,
        question_id: int,
        admin_user_id: int,
    ) -> AdminQuestionReviewOut:
        self._require_admin(admin_user_id)
        question = self._get_question_with_annotations(question_id, with_for_update=False)
        return self._serialize_admin_question_review(question)

    def approve_admin_question_review(
        self,
        question_id: int,
        payload: AdminReviewDecisionRequest,
    ) -> AdminQuestionReviewOut:
        self._require_admin(payload.admin_user_id)
        question = self._get_question_with_annotations(question_id, with_for_update=True)
        final_annotations = self._final_annotations(question.id)
        if len(final_annotations) < question.required_annotations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="当前题目尚未达到要求标注人数，不能直接审核通过。",
            )
        aggregate = self._aggregate_question(question, final_annotations)
        aggregate.is_disputed = False
        aggregate.finalized_at = datetime.utcnow()
        question.annotation_status = QUESTION_STATUS_COMPLETED
        self._close_open_review_tasks(
            question.id,
            review_comment=payload.review_comment or "管理员审核通过当前聚合结论。",
        )
        self._append_review_log(
            question_id=question.id,
            aggregate_id=aggregate.id,
            actor_user=self._require_user(payload.admin_user_id),
            action_code="ADMIN_APPROVED",
            comment=payload.review_comment,
            detail_json={
                "completed_annotation_count": len(final_annotations),
                "required_annotations": question.required_annotations,
            },
        )
        self.db.commit()
        refreshed = self._get_question_with_annotations(question_id, with_for_update=False)
        return self._serialize_admin_question_review(refreshed)

    def reject_admin_question_review(
        self,
        question_id: int,
        payload: AdminReviewDecisionRequest,
    ) -> AdminQuestionReviewOut:
        self._require_admin(payload.admin_user_id)
        question = self._get_question_with_annotations(question_id, with_for_update=True)
        final_annotations = self._final_annotations(question.id)
        if not final_annotations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="当前题目还没有可打回的标注结果。",
            )
        question.required_annotations = max(
            question.required_annotations,
            len(final_annotations),
        ) + payload.additional_annotations
        question.annotation_count = len(final_annotations)
        question.annotation_status = QUESTION_STATUS_WAITING
        aggregate = self.db.scalar(
            select(QuestionLabelAggregate).where(QuestionLabelAggregate.question_id == question.id)
        )
        if aggregate is not None:
            aggregate.is_disputed = True
            aggregate.finalized_at = None
        self._close_open_review_tasks(
            question.id,
            review_comment=payload.review_comment or "管理员打回，补充更多标注后重新聚合。",
        )
        self._append_review_log(
            question_id=question.id,
            aggregate_id=aggregate.id if aggregate is not None else None,
            actor_user=self._require_user(payload.admin_user_id),
            action_code="ADMIN_REJECTED_FOR_REANNOTATION",
            comment=payload.review_comment,
            detail_json={
                "new_required_annotations": question.required_annotations,
                "additional_annotations": payload.additional_annotations,
                "submitted_annotation_count": question.annotation_count,
            },
        )
        self.db.commit()
        refreshed = self._get_question_with_annotations(question_id, with_for_update=False)
        return self._serialize_admin_question_review(refreshed)

    def override_admin_question_review(
        self,
        question_id: int,
        payload: AdminAggregateOverrideRequest,
    ) -> AdminQuestionReviewOut:
        admin_user = self._require_admin(payload.admin_user_id)
        question = self._get_question_with_annotations(question_id, with_for_update=True)
        final_annotations = self._final_annotations(question.id)
        self._validate_cognitive_level_id(payload.final_cognitive_level_id)
        self._validate_competencies(payload.competencies)

        if final_annotations:
            aggregate = self.db.scalar(
                select(QuestionLabelAggregate)
                .options(
                    selectinload(QuestionLabelAggregate.competencies).selectinload(
                        QuestionAggregateCompetency.competency
                    )
                )
                .where(QuestionLabelAggregate.question_id == question.id)
            )
            if aggregate is None:
                aggregate = self._aggregate_question(question, final_annotations)

            self.db.execute(
                delete(QuestionAggregateCompetency).where(
                    QuestionAggregateCompetency.aggregate_id == aggregate.id
                )
            )
            self.db.flush()

            for competency in payload.competencies:
                self.db.add(
                    QuestionAggregateCompetency(
                        aggregate_id=aggregate.id,
                        competency_id=competency.competency_id,
                        level_value=competency.level_value,
                        agreement_score=None,
                    )
                )

            aggregate.final_cognitive_level_id = payload.final_cognitive_level_id
            aggregate.completed_annotation_count = len(final_annotations)
            aggregate.is_disputed = False
            aggregate.finalized_at = datetime.utcnow()
            question.annotation_status = QUESTION_STATUS_COMPLETED
            question.annotation_count = len(final_annotations)
            aggregate_id = aggregate.id
            detail_json = {
                "result_source": "aggregate",
                "final_cognitive_level_id": payload.final_cognitive_level_id,
                "competency_count": len(payload.competencies),
                "completed_annotation_count": len(final_annotations),
            }
        else:
            gold_label = self.db.scalar(
                select(QuestionGoldLabel)
                .options(
                    selectinload(QuestionGoldLabel.competencies).selectinload(
                        QuestionGoldCompetency.competency
                    )
                )
                .where(QuestionGoldLabel.question_id == question.id)
            )
            if gold_label is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="当前题目还没有可修改的标注结果。",
                )
            self.db.execute(
                delete(QuestionGoldCompetency).where(
                    QuestionGoldCompetency.gold_label_id == gold_label.id
                )
            )
            self.db.flush()
            for competency in payload.competencies:
                self.db.add(
                    QuestionGoldCompetency(
                        gold_label_id=gold_label.id,
                        competency_id=competency.competency_id,
                        level_value=competency.level_value,
                    )
                )
            gold_label.cognitive_level_id = payload.final_cognitive_level_id
            gold_label.label_source = "ADMIN_OVERRIDE"
            aggregate_id = None
            detail_json = {
                "result_source": "gold_label",
                "final_cognitive_level_id": payload.final_cognitive_level_id,
                "competency_count": len(payload.competencies),
                "gold_label_id": gold_label.id,
            }

        self._close_open_review_tasks(
            question.id,
            review_comment=payload.review_comment or "管理员已手动修改最终标注结果。",
        )
        self._append_review_log(
            question_id=question.id,
            aggregate_id=aggregate_id,
            actor_user=admin_user,
            action_code="ADMIN_OVERRIDE_FINAL_RESULT",
            comment=payload.review_comment,
            detail_json=detail_json,
        )
        self.db.commit()
        refreshed = self._get_question_with_annotations(question_id, with_for_update=False)
        return self._serialize_admin_question_review(refreshed)

    def _load_candidate_ids(self, data_scope: str) -> list[int]:
        stmt = (
            select(Question.id)
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .where(Question.source_status == "ACTIVE")
            .where(QuestionContent.stem_text != "")
            .order_by(Question.id.asc())
        )
        if data_scope == "pending":
            stmt = stmt.where(Question.annotation_status == QUESTION_STATUS_PENDING)
        return list(self.db.scalars(stmt))

    def _load_candidates_by_ids(self, question_ids: list[int]) -> list[CoresetCandidate]:
        if not question_ids:
            return []

        questions = list(
            self.db.scalars(
                select(Question)
                .join(QuestionContent, QuestionContent.question_id == Question.id)
                .options(selectinload(Question.content))
                .where(Question.id.in_(question_ids))
                .order_by(Question.id.asc())
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

    def _sample_candidate_ids(self, candidate_ids: list[int], limit: int) -> list[int]:
        if len(candidate_ids) <= limit:
            return candidate_ids

        rng = random.Random(self.selector.seed)
        sampled_positions = sorted(rng.sample(range(len(candidate_ids)), limit))
        return [candidate_ids[index] for index in sampled_positions]

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
                .options(
                    selectinload(Annotation.user),
                    selectinload(Annotation.competencies).selectinload(
                        AnnotationCompetency.competency
                    ),
                )
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
        consensus = self._build_consensus_summary(
            annotations,
            required_annotations=question.required_annotations,
        )

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

        for dimension in consensus.dimensions:
            if dimension.dimension_type != "competency":
                continue
            competency_id = int(dimension.dimension_key)
            self.db.add(
                QuestionAggregateCompetency(
                    aggregate_id=aggregate.id,
                    competency_id=competency_id,
                    level_value=int(dimension.recommended_level_value or 0),
                    agreement_score=Decimal(f"{dimension.agreement_score:.2f}"),
                )
            )

        cognitive_dimension = next(
            (item for item in consensus.dimensions if item.dimension_type == "cognitive_level"),
            None,
        )
        aggregate.final_cognitive_level_id = (
            cognitive_dimension.recommended_level_value if cognitive_dimension else None
        )
        aggregate.completed_annotation_count = len(annotations)
        aggregate.agreement_score = (
            Decimal(f"{consensus.agreement_score:.2f}")
            if consensus.agreement_score is not None
            else None
        )
        aggregate.is_disputed = consensus.consensus_status == "DISPUTED"
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
                self._append_review_log(
                    question_id=question.id,
                    aggregate_id=aggregate.id,
                    action_code="AUTO_REVIEW_CREATED",
                    detail_json={
                        "consensus_status": consensus.consensus_status,
                        "unresolved_dimension_count": consensus.unresolved_dimension_count,
                    },
                )
        else:
            self._close_open_review_tasks(
                question.id,
                review_comment="多数一致，系统自动完成聚合并关闭待处理复核任务。",
            )
        if not aggregate.is_disputed:
            self._append_review_log(
                question_id=question.id,
                aggregate_id=aggregate.id,
                action_code="AUTO_CONSENSUS_COMPLETED",
                detail_json={
                    "consensus_status": consensus.consensus_status,
                    "agreement_score": consensus.agreement_score,
                },
            )
        return aggregate

    def _serialize_review_task(self, review_task_id: int) -> ReviewTaskOut:
        task = self.db.scalar(
            select(ReviewTask)
            .options(
                selectinload(ReviewTask.question).selectinload(Question.subject),
                selectinload(ReviewTask.question).selectinload(Question.grade),
                selectinload(ReviewTask.question).selectinload(Question.question_type),
                selectinload(ReviewTask.question).selectinload(Question.content),
                selectinload(ReviewTask.aggregate)
                .selectinload(QuestionLabelAggregate.competencies)
                .selectinload(QuestionAggregateCompetency.competency),
            )
            .where(ReviewTask.id == review_task_id)
        )
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="复核任务不存在")
        return ReviewTaskOut(
            id=task.id,
            question_id=task.question_id,
            aggregate_id=task.aggregate_id,
            reviewer_id=task.reviewer_id,
            review_status=task.review_status,
            review_comment=task.review_comment,
            created_at=task.created_at,
            reviewed_at=task.reviewed_at,
            question=task.question,
            aggregate=self._serialize_aggregate(task.aggregate),
            annotations=self._serialize_review_annotations(task.question_id),
            consensus=self._build_consensus_summary(
                self._final_annotations(task.question_id),
                required_annotations=task.question.required_annotations,
            ),
            review_logs=self._serialize_review_logs(task.question_id),
        )

    def _serialize_aggregate(self, aggregate: QuestionLabelAggregate) -> AnnotationAggregateOut:
        return AnnotationAggregateOut(
            id=aggregate.id,
            question_id=aggregate.question_id,
            final_cognitive_level_id=aggregate.final_cognitive_level_id,
            agreement_score=float(aggregate.agreement_score)
            if aggregate.agreement_score is not None
            else None,
            is_disputed=aggregate.is_disputed,
            completed_annotation_count=aggregate.completed_annotation_count,
            finalized_at=aggregate.finalized_at,
            competencies=[
                AnnotationAggregateCompetencyOut(
                    competency_id=item.competency_id,
                    competency_name=item.competency.name
                    if item.competency
                    else str(item.competency_id),
                    level_value=item.level_value,
                    agreement_score=float(item.agreement_score)
                    if item.agreement_score is not None
                    else None,
                )
                for item in aggregate.competencies
            ],
        )

    def _serialize_review_annotations(self, question_id: int) -> list[ReviewAnnotationOut]:
        annotations = list(
            self.db.scalars(
                select(Annotation)
                .options(
                    selectinload(Annotation.user),
                    selectinload(Annotation.competencies).selectinload(
                        AnnotationCompetency.competency
                    ),
                )
                .where(Annotation.question_id == question_id)
                .where(Annotation.is_final.is_(True))
                .order_by(Annotation.created_at.asc(), Annotation.id.asc())
            ).unique()
        )
        return [
            ReviewAnnotationOut(
                annotation_id=annotation.id,
                user_id=annotation.user_id,
                user_name=annotation.user.real_name or annotation.user.username,
                cognitive_level_id=annotation.cognitive_level_id,
                confidence_level=annotation.confidence_level,
                submitted_at=annotation.created_at,
                competencies=[
                    ReviewAnnotationCompetencyOut(
                        competency_id=item.competency_id,
                        competency_name=item.competency.name
                        if item.competency
                        else str(item.competency_id),
                        level_value=item.level_value,
                    )
                    for item in annotation.competencies
                ],
            )
            for annotation in annotations
        ]

    def _serialize_admin_annotations(self, question_id: int) -> list[AdminQuestionAnnotationOut]:
        annotations = list(
            self.db.scalars(
                select(Annotation)
                .options(
                    selectinload(Annotation.user),
                    selectinload(Annotation.task),
                    selectinload(Annotation.competencies).selectinload(
                        AnnotationCompetency.competency
                    ),
                )
                .where(Annotation.question_id == question_id)
                .where(Annotation.is_final.is_(True))
                .order_by(Annotation.created_at.asc(), Annotation.id.asc())
            ).unique()
        )
        return [
            AdminQuestionAnnotationOut(
                annotation_id=annotation.id,
                task_id=annotation.task_id,
                task_status=annotation.task.task_status if annotation.task else None,
                user_id=annotation.user_id,
                user_name=annotation.user.real_name or annotation.user.username,
                cognitive_level_id=annotation.cognitive_level_id,
                confidence_level=annotation.confidence_level,
                submitted_at=annotation.created_at,
                competencies=[
                    ReviewAnnotationCompetencyOut(
                        competency_id=item.competency_id,
                        competency_name=item.competency.name
                        if item.competency
                        else str(item.competency_id),
                        level_value=item.level_value,
                    )
                    for item in annotation.competencies
                ],
            )
            for annotation in annotations
        ]

    def _serialize_annotation_task(self, task: AnnotationTask) -> AnnotationTaskOut:
        progress = self._build_progress(
            submitted_annotation_count=task.question.annotation_count,
            active_annotation_count=self._active_task_count(task.question_id),
            required_annotations=task.question.required_annotations,
        )
        return AnnotationTaskOut(
            id=task.id,
            question_id=task.question_id,
            assignee_id=task.assignee_id,
            source_batch_id=task.source_batch_id,
            task_status=task.task_status,
            assigned_at=task.assigned_at,
            started_at=task.started_at,
            submitted_at=task.submitted_at,
            question=task.question,
            progress=progress,
        )

    def _serialize_annotator_history_item(
        self,
        annotation: Annotation,
    ) -> AnnotatorHistoryItemOut:
        aggregate = self.db.scalar(
            select(QuestionLabelAggregate)
            .options(
                selectinload(QuestionLabelAggregate.competencies).selectinload(
                    QuestionAggregateCompetency.competency
                )
            )
            .where(QuestionLabelAggregate.question_id == annotation.question_id)
        )
        review_state = self._annotator_review_state(annotation.question_id, annotation.question.annotation_status)
        adoption_status = self._annotator_adoption_status(annotation, aggregate)
        annotation_detail = ReviewAnnotationOut(
            annotation_id=annotation.id,
            user_id=annotation.user_id,
            user_name=annotation.user.real_name or annotation.user.username,
            cognitive_level_id=annotation.cognitive_level_id,
            confidence_level=annotation.confidence_level,
            submitted_at=annotation.created_at,
            competencies=[
                ReviewAnnotationCompetencyOut(
                    competency_id=item.competency_id,
                    competency_name=item.competency.name
                    if item.competency
                    else str(item.competency_id),
                    level_value=item.level_value,
                )
                for item in annotation.competencies
            ],
        )
        return AnnotatorHistoryItemOut(
            annotation_id=annotation.id,
            task_id=annotation.task_id,
            question_id=annotation.question_id,
            submitted_at=annotation.created_at,
            confidence_level=annotation.confidence_level,
            question_status=annotation.question.annotation_status,
            review_state=review_state,
            adoption_status=adoption_status,
            question=annotation.question,
            annotation=annotation_detail,
            final_aggregate=self._serialize_aggregate(aggregate) if aggregate is not None else None,
            review_logs=self._serialize_review_logs(annotation.question_id),
        )

    def _serialize_admin_question_review(self, question: Question) -> AdminQuestionReviewOut:
        annotations = self._final_annotations(question.id)
        active_annotation_count = self._active_task_count(question.id)
        aggregate = self.db.scalar(
            select(QuestionLabelAggregate)
            .options(
                selectinload(QuestionLabelAggregate.competencies).selectinload(
                    QuestionAggregateCompetency.competency
                )
            )
            .where(QuestionLabelAggregate.question_id == question.id)
        )
        gold_label = self.db.scalar(
            select(QuestionGoldLabel)
            .options(
                selectinload(QuestionGoldLabel.competencies).selectinload(
                    QuestionGoldCompetency.competency
                )
            )
            .where(QuestionGoldLabel.question_id == question.id)
        )
        return AdminQuestionReviewOut(
            question_id=question.id,
            annotation_status=question.annotation_status,
            submitted_annotation_count=question.annotation_count,
            active_annotation_count=active_annotation_count,
            required_annotations=question.required_annotations,
            remaining_annotation_count=max(
                question.required_annotations - question.annotation_count - active_annotation_count,
                0,
            ),
            open_review_task_count=self._open_review_task_count(question.id),
            aggregate=self._serialize_aggregate(aggregate) if aggregate is not None else None,
            gold_label=self._serialize_gold_label(gold_label) if gold_label is not None else None,
            consensus=self._build_consensus_summary(
                annotations,
                required_annotations=question.required_annotations,
            ),
            annotations=self._serialize_admin_annotations(question.id),
            review_logs=self._serialize_review_logs(question.id),
        )

    def _serialize_gold_label(self, gold_label: QuestionGoldLabel) -> AnnotationAggregateOut:
        return AnnotationAggregateOut(
            id=gold_label.id,
            question_id=gold_label.question_id,
            final_cognitive_level_id=gold_label.cognitive_level_id,
            agreement_score=None,
            is_disputed=False,
            completed_annotation_count=1,
            finalized_at=gold_label.imported_at,
            competencies=[
                AnnotationAggregateCompetencyOut(
                    competency_id=item.competency_id,
                    competency_name=item.competency.name
                    if item.competency
                    else str(item.competency_id),
                    level_value=item.level_value,
                    agreement_score=None,
                )
                for item in gold_label.competencies
            ],
        )

    def _serialize_review_logs(self, question_id: int) -> list[AnnotationReviewLogOut]:
        logs = list(
            self.db.scalars(
                select(AnnotationReviewLog)
                .options(selectinload(AnnotationReviewLog.actor_user))
                .where(AnnotationReviewLog.question_id == question_id)
                .order_by(AnnotationReviewLog.created_at.desc(), AnnotationReviewLog.id.desc())
            )
        )
        return [
            AnnotationReviewLogOut(
                id=log.id,
                question_id=log.question_id,
                aggregate_id=log.aggregate_id,
                review_task_id=log.review_task_id,
                actor_user_id=log.actor_user_id,
                actor_name=(
                    log.actor_user.real_name or log.actor_user.username
                    if log.actor_user is not None
                    else "系统"
                ),
                actor_role=log.actor_role,
                action_code=log.action_code,
                action_label=ACTION_LABELS.get(log.action_code, log.action_code),
                comment=log.comment,
                detail_json=log.detail_json,
                created_at=log.created_at,
            )
            for log in logs
        ]

    def _annotator_review_state(
        self,
        question_id: int,
        question_status: str,
    ) -> str:
        completed_review_count = self.db.scalar(
            select(func.count())
            .select_from(ReviewTask)
            .where(ReviewTask.question_id == question_id)
            .where(ReviewTask.review_status == REVIEW_STATUS_COMPLETED)
        ) or 0
        if completed_review_count > 0:
            return "COMPLETED"
        if question_status == QUESTION_STATUS_REVIEW_PENDING:
            return "PENDING"
        return "NOT_REQUIRED"

    def _annotator_adoption_status(
        self,
        annotation: Annotation,
        aggregate: QuestionLabelAggregate | None,
    ) -> str:
        if aggregate is None or annotation.question.annotation_status != QUESTION_STATUS_COMPLETED:
            return "PENDING"
        final_competency_map = {
            item.competency_id: int(item.level_value) for item in aggregate.competencies
        }
        annotation_competency_map = {
            item.competency_id: int(item.level_value) for item in annotation.competencies
        }
        competency_ids = set(final_competency_map) | set(annotation_competency_map)
        competency_match = all(
            annotation_competency_map.get(competency_id, 0) == final_competency_map.get(competency_id, 0)
            for competency_id in competency_ids
        )
        cognitive_match = (
            annotation.cognitive_level_id == aggregate.final_cognitive_level_id
        )
        return "PASSED" if competency_match and cognitive_match else "OVERRIDDEN"

    def _append_review_log(
        self,
        *,
        question_id: int,
        action_code: str,
        aggregate_id: int | None = None,
        review_task_id: int | None = None,
        actor_user: User | None = None,
        comment: str | None = None,
        detail_json: dict | None = None,
    ) -> None:
        self.db.add(
            AnnotationReviewLog(
                question_id=question_id,
                aggregate_id=aggregate_id,
                review_task_id=review_task_id,
                actor_user_id=actor_user.id if actor_user is not None else None,
                actor_role=actor_user.role.code if actor_user is not None and actor_user.role else "system",
                action_code=action_code,
                comment=comment,
                detail_json=detail_json,
            )
        )

    def _majority(self, values: list[int | None]) -> tuple[int | None, float]:
        if not values:
            return None, 0.0
        counter = Counter(values)
        value, count = counter.most_common(1)[0]
        return value, count / len(values)

    def _build_consensus_summary(
        self,
        annotations: list[Annotation],
        *,
        required_annotations: int,
    ) -> AnnotationConsensusSummaryOut:
        if not annotations:
            return AnnotationConsensusSummaryOut(
                agreement_score=None,
                consensus_status="INSUFFICIENT",
                completed_annotation_count=0,
                required_annotations=required_annotations,
                unresolved_dimension_count=0,
                dimensions=[],
            )

        confidence_map = {
            annotation.id: float(annotation.confidence_level or 3)
            for annotation in annotations
        }
        annotator_name_map = {
            annotation.id: (
                annotation.user.real_name or annotation.user.username
                if annotation.user is not None
                else f"用户{annotation.user_id}"
            )
            for annotation in annotations
        }
        dimensions: list[AnnotationConsensusDimensionOut] = []

        cognitive_values = [
            (annotation.id, annotation.cognitive_level_id)
            for annotation in annotations
            if annotation.cognitive_level_id is not None
        ]
        if cognitive_values:
            dimensions.append(
                self._build_consensus_dimension(
                    dimension_type="cognitive_level",
                    dimension_key="cognitive_level",
                    dimension_label="认知层级",
                    votes=cognitive_values,
                    confidence_map=confidence_map,
                    annotator_name_map=annotator_name_map,
                )
            )

        competency_labels = self._competency_label_map()
        competency_votes: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for annotation in annotations:
            for item in annotation.competencies:
                competency_votes[item.competency_id].append((annotation.id, item.level_value))

        for competency_id in sorted(competency_votes):
            dimensions.append(
                self._build_consensus_dimension(
                    dimension_type="competency",
                    dimension_key=str(competency_id),
                    dimension_label=competency_labels.get(competency_id, str(competency_id)),
                    votes=competency_votes[competency_id],
                    confidence_map=confidence_map,
                    annotator_name_map=annotator_name_map,
                )
            )

        unresolved_count = sum(1 for item in dimensions if item.consensus_status == "DISPUTED")
        exact_count = sum(1 for item in dimensions if item.consensus_status == "UNANIMOUS")
        agreement_score = (
            sum(item.agreement_score for item in dimensions) / len(dimensions)
            if dimensions
            else None
        )
        if len(annotations) < required_annotations:
            consensus_status = "INSUFFICIENT"
        elif unresolved_count > 0:
            consensus_status = "DISPUTED"
        elif exact_count == len(dimensions):
            consensus_status = "UNANIMOUS"
        else:
            consensus_status = "MAJORITY"

        return AnnotationConsensusSummaryOut(
            agreement_score=agreement_score,
            consensus_status=consensus_status,
            completed_annotation_count=len(annotations),
            required_annotations=required_annotations,
            unresolved_dimension_count=unresolved_count,
            dimensions=dimensions,
        )

    def _build_consensus_dimension(
        self,
        *,
        dimension_type: str,
        dimension_key: str,
        dimension_label: str,
        votes: list[tuple[int, int | None]],
        confidence_map: dict[int, float],
        annotator_name_map: dict[int, str],
    ) -> AnnotationConsensusDimensionOut:
        vote_buckets: dict[int | None, list[int]] = defaultdict(list)
        weighted_scores: dict[int | None, float] = defaultdict(float)
        for annotation_id, level_value in votes:
            vote_buckets[level_value].append(annotation_id)
            weighted_scores[level_value] += confidence_map.get(annotation_id, 3.0)

        sorted_votes = sorted(
            vote_buckets.items(),
            key=lambda item: (
                -len(item[1]),
                -weighted_scores[item[0]],
                -(item[0] if item[0] is not None else -1),
            ),
        )
        recommended_level_value = sorted_votes[0][0]
        recommended_vote_count = len(sorted_votes[0][1])
        agreement_score = recommended_vote_count / len(votes)
        if recommended_vote_count == len(votes):
            consensus_status = "UNANIMOUS"
        elif recommended_vote_count >= 2:
            consensus_status = "MAJORITY"
        else:
            consensus_status = "DISPUTED"

        return AnnotationConsensusDimensionOut(
            dimension_type=dimension_type,
            dimension_key=dimension_key,
            dimension_label=dimension_label,
            recommended_level_value=recommended_level_value,
            agreement_score=agreement_score,
            consensus_status=consensus_status,
            vote_summary=[
                AnnotationConsensusVoteOut(
                    level_value=level_value,
                    vote_count=len(annotation_ids),
                    annotator_names=[
                        annotator_name_map.get(annotation_id, f"用户{annotation_id}")
                        for annotation_id in annotation_ids
                    ],
                    weighted_score=weighted_scores[level_value],
                )
                for level_value, annotation_ids in sorted(
                    vote_buckets.items(),
                    key=lambda item: (-len(item[1]), -(item[0] if item[0] is not None else -1)),
                )
            ],
        )

    def _build_progress(
        self,
        *,
        submitted_annotation_count: int,
        active_annotation_count: int,
        required_annotations: int,
    ) -> AnnotationTaskProgressOut:
        completed_slots = min(
            required_annotations,
            submitted_annotation_count + active_annotation_count,
        )
        percent = (
            round((completed_slots / required_annotations) * 100, 2)
            if required_annotations > 0
            else 0.0
        )
        return AnnotationTaskProgressOut(
            submitted_annotation_count=submitted_annotation_count,
            active_annotation_count=active_annotation_count,
            required_annotations=required_annotations,
            remaining_annotation_count=max(
                required_annotations - submitted_annotation_count - active_annotation_count,
                0,
            ),
            progress_percent=percent,
        )

    def _active_task_count(self, question_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.count(AnnotationTask.id))
                .where(AnnotationTask.question_id == question_id)
                .where(AnnotationTask.task_status == TASK_STATUS_IN_PROGRESS)
            )
            or 0
        )

    def _open_review_task_count(self, question_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.count(ReviewTask.id))
                .where(ReviewTask.question_id == question_id)
                .where(ReviewTask.review_status.in_([REVIEW_STATUS_PENDING, REVIEW_STATUS_IN_PROGRESS]))
            )
            or 0
        )

    def _close_open_review_tasks(
        self,
        question_id: int,
        *,
        exclude_review_task_id: int | None = None,
        review_comment: str | None = None,
    ) -> None:
        review_tasks = list(
            self.db.scalars(
                select(ReviewTask)
                .where(ReviewTask.question_id == question_id)
                .where(ReviewTask.review_status.in_([REVIEW_STATUS_PENDING, REVIEW_STATUS_IN_PROGRESS]))
            )
        )
        now = datetime.utcnow()
        for task in review_tasks:
            if exclude_review_task_id is not None and task.id == exclude_review_task_id:
                continue
            task.review_status = REVIEW_STATUS_COMPLETED
            if review_comment and not task.review_comment:
                task.review_comment = review_comment
            task.reviewed_at = now
            self._append_review_log(
                question_id=question_id,
                aggregate_id=task.aggregate_id,
                review_task_id=task.id,
                action_code="AUTO_REVIEW_CLOSED",
                comment=review_comment,
            )

    def _competency_label_map(self) -> dict[int, str]:
        rows = self.db.execute(select(Competency.id, Competency.name)).all()
        return {int(competency_id): str(name) for competency_id, name in rows}

    def _get_question_with_annotations(
        self,
        question_id: int,
        *,
        with_for_update: bool,
    ) -> Question:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.subject),
                selectinload(Question.grade),
                selectinload(Question.question_type),
                selectinload(Question.content),
            )
            .where(Question.id == question_id)
        )
        if with_for_update:
            stmt = stmt.with_for_update()
        question = self.db.scalar(stmt)
        if question is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在。")
        return question

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

    def _validate_cognitive_level_id(self, cognitive_level_id: int | None) -> None:
        if cognitive_level_id is None:
            return
        cognitive_level_exists = self.db.scalar(
            select(func.count())
            .select_from(CognitiveLevel)
            .where(CognitiveLevel.id == cognitive_level_id)
        )
        if not cognitive_level_exists:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="存在无效的认知层级。",
            )

    def _serialize_selection_batch(self, batch: RecommendationBatch) -> SelectionBatchSummaryOut:
        question_ids = list(
            self.db.scalars(
                select(RecommendationItem.question_id).where(RecommendationItem.batch_id == batch.id)
            )
        )
        counts = self._question_status_counts(question_ids)
        return SelectionBatchSummaryOut(
            id=batch.id,
            batch_no=batch.batch_no,
            algorithm_code=batch.algorithm_code,
            triggered_by_user_id=batch.triggered_by_user_id,
            created_at=batch.created_at,
            requested_count=int((batch.context_json or {}).get("requested_count") or len(question_ids)),
            candidate_count=int((batch.context_json or {}).get("candidate_count") or len(question_ids)),
            selected_count=len(question_ids),
            pending_count=counts.get(QUESTION_STATUS_PENDING, 0),
            waiting_count=counts.get(QUESTION_STATUS_WAITING, 0),
            in_progress_count=counts.get(QUESTION_STATUS_IN_PROGRESS, 0),
            question_ids=question_ids,
        )

    def _question_status_counts(self, question_ids: list[int]) -> dict[str, int]:
        if not question_ids:
            return {}
        rows = self.db.execute(
            select(Question.annotation_status, func.count(Question.id))
            .where(Question.id.in_(question_ids))
            .group_by(Question.annotation_status)
        ).all()
        return {str(status_code): int(count) for status_code, count in rows}

    def _reset_question_pool(
        self,
        *,
        question_ids: list[int] | None = None,
        source_batch_id: int | None = None,
    ) -> dict[str, int]:
        recalled_in_progress_count = 0
        returned_waiting_count = 0

        task_stmt = (
            select(AnnotationTask)
            .options(selectinload(AnnotationTask.question))
            .where(AnnotationTask.task_status == TASK_STATUS_IN_PROGRESS)
        )
        if source_batch_id is not None:
            task_stmt = task_stmt.where(AnnotationTask.source_batch_id == source_batch_id)
        if question_ids is not None:
            task_stmt = task_stmt.where(AnnotationTask.question_id.in_(question_ids))

        tasks = list(self.db.scalars(task_stmt).unique())
        for task in tasks:
            if task.question and task.question.annotation_count > 0:
                continue
            task.task_status = TASK_STATUS_RECALLED
            if task.question:
                task.question.annotation_status = QUESTION_STATUS_PENDING
                recalled_in_progress_count += 1

        waiting_stmt = select(Question).where(
            Question.annotation_status == QUESTION_STATUS_WAITING,
            Question.annotation_count == 0,
        )
        if question_ids is not None:
            waiting_stmt = waiting_stmt.where(Question.id.in_(question_ids))

        waiting_questions = list(self.db.scalars(waiting_stmt))
        if source_batch_id is not None:
            waiting_questions = [
                question
                for question in waiting_questions
                if self._latest_source_batch_id(question.id) == source_batch_id
            ]
        for question in waiting_questions:
            question.annotation_status = QUESTION_STATUS_PENDING
            returned_waiting_count += 1

        return {
            "recalled_in_progress_count": recalled_in_progress_count,
            "returned_waiting_count": returned_waiting_count,
            "reset_to_pending_count": recalled_in_progress_count + returned_waiting_count,
        }

    def _require_user(self, user_id: int) -> User:
        user = self.db.scalar(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        return user

    def _require_admin(self, user_id: int) -> User:
        user = self._require_user(user_id)
        if user.role.code != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有系统管理员可以执行该操作。",
            )
        return user

    def _require_annotator(self, user: User) -> None:
        if user.role.code != "annotator":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有标注员可以领取和提交普通标注任务",
            )

    def _require_reviewer(self, user: User) -> None:
        if user.role.code != "reviewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有复核员可以领取和提交标注复核任务",
            )

    def _allowed_training_stages(self, user: User) -> list[str] | None:
        if user.role.code != "annotator":
            return None
        if user.training_scope == "both":
            return ["junior", "senior"]
        if user.training_scope in {"junior", "senior"}:
            return [user.training_scope]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="标注员尚未完成培训，请先通过培训考核后再领取题目。",
        )

    def _ensure_training_access_for_question(self, user: User, question: Question) -> None:
        if user.role.code != "annotator":
            return
        stage = question.grade.edu_stage if question.grade else None
        if stage is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="当前题目尚未判定学段，暂不能进入标注流程。",
            )
        if not training_scope_allows_stage(user.training_scope, stage):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前标注员未通过该学段培训，不能提交此题标注。",
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
