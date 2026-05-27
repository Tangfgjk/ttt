from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.pagination import PageMeta
from app.schemas.question import QuestionListItem

AnnotationPoolStatus = Literal[
    "PENDING",
    "WAITING",
    "IN_PROGRESS",
    "REVIEW_PENDING",
    "COMPLETED",
]

SelectionStrategy = Literal[
    "random",
    "kmeans",
    "facility_location",
    "graph_cut",
    "moe",
]
SelectionDataScope = Literal["all", "pending"]
AnnotatorCount = Literal[1, 2, 3]


class PoolSummaryItem(BaseModel):
    status: AnnotationPoolStatus
    count: int


class PoolSummaryResponse(BaseModel):
    items: list[PoolSummaryItem]


class AnnotationPolicySettingsOut(BaseModel):
    annotator_count: AnnotatorCount
    review_required: bool
    strategy_description: str
    sync_status: "AnnotationPolicySyncStatusOut"


class AnnotationPolicySyncStatusOut(BaseModel):
    status: Literal["idle", "running", "completed", "failed"]
    target_annotator_count: AnnotatorCount
    affected_question_count: int
    updated_question_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


class AnnotationPolicyUpdateRequest(BaseModel):
    admin_user_id: int
    annotator_count: AnnotatorCount


class AnnotationPolicyUpdateResponse(AnnotationPolicySettingsOut):
    affected_question_count: int


class WorkspaceSummaryOut(BaseModel):
    user_id: int
    role: str
    pending_task_count: int
    completed_today_count: int
    escalated_count: int = 0
    completed_review_count: int = 0


class SelectionStrategyItem(BaseModel):
    code: SelectionStrategy
    name: str
    description: str


class AdminSelectionRequest(BaseModel):
    strategy: SelectionStrategy = "kmeans"
    count: int = Field(default=100, ge=1)
    data_scope: SelectionDataScope = "pending"
    triggered_by_user_id: int | None = None


class AdminSelectionResponse(BaseModel):
    batch_id: int
    batch_no: str
    strategy: SelectionStrategy
    requested_count: int
    selected_count: int
    moved_count: int
    candidate_count: int
    question_ids: list[int]
    moved_question_ids: list[int]


class SelectionBatchSummaryOut(BaseModel):
    id: int
    batch_no: str
    algorithm_code: str
    source_run_no: str | None = None
    triggered_by_user_id: int | None = None
    created_at: datetime
    requested_count: int
    candidate_count: int
    selected_count: int
    pending_count: int
    waiting_count: int
    in_progress_count: int
    question_ids: list[int]


class AdminPoolResetRequest(BaseModel):
    admin_user_id: int


class AdminPoolResetResponse(BaseModel):
    recalled_in_progress_count: int
    returned_waiting_count: int
    reset_to_pending_count: int


class SelectionBatchRollbackRequest(BaseModel):
    admin_user_id: int


class SelectionBatchRollbackResponse(BaseModel):
    batch_id: int
    batch_no: str
    recalled_in_progress_count: int
    returned_waiting_count: int
    reset_to_pending_count: int


class ClaimAnnotationRequest(BaseModel):
    annotator_user_id: int
    count: int = Field(default=50, ge=1)


class ClaimAnnotationResponse(BaseModel):
    claimed_count: int
    task_ids: list[int]
    items: list["AnnotationTaskOut"]


class AnnotationCompetencyInput(BaseModel):
    competency_id: int
    level_value: int = Field(ge=0, le=3)
    confidence_level: int = Field(default=5, ge=1, le=5)


class SubmitAnnotationRequest(BaseModel):
    annotator_user_id: int
    cognitive_level_id: int | None = None
    competencies: list[AnnotationCompetencyInput] = Field(default_factory=list)
    confidence_level: int | None = Field(default=None, ge=1, le=5)
    time_spent_seconds: int | None = Field(default=None, ge=0)


class SubmitAnnotationResponse(BaseModel):
    annotation_id: int
    question_id: int
    annotation_count: int
    required_annotations: int
    question_status: AnnotationPoolStatus
    aggregate_id: int | None = None
    is_disputed: bool = False


class AnnotationTaskProgressOut(BaseModel):
    submitted_annotation_count: int
    active_annotation_count: int
    required_annotations: int
    remaining_annotation_count: int
    progress_percent: float


class AnnotationTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    assignee_id: int
    source_batch_id: int | None = None
    task_status: str
    assigned_at: datetime
    started_at: datetime | None = None
    submitted_at: datetime | None = None
    question: QuestionListItem
    progress: AnnotationTaskProgressOut


class AnnotationTaskListResponse(BaseModel):
    items: list[AnnotationTaskOut]
    meta: PageMeta


class AnnotatorHistoryItemOut(BaseModel):
    annotation_id: int
    task_id: int | None = None
    question_id: int
    submitted_at: datetime
    confidence_level: int | None = None
    question_status: AnnotationPoolStatus
    review_state: Literal["NOT_REQUIRED", "PENDING", "COMPLETED"]
    adoption_status: Literal["PENDING", "PASSED", "OVERRIDDEN"]
    question: QuestionListItem
    annotation: ReviewAnnotationOut
    final_aggregate: AnnotationAggregateOut | None = None
    review_logs: list["AnnotationReviewLogOut"]


class AnnotatorHistoryListResponse(BaseModel):
    items: list[AnnotatorHistoryItemOut]
    meta: PageMeta


AnnotatorHistoryReviewState = Literal["NOT_REQUIRED", "PENDING", "COMPLETED"]
AnnotatorHistoryAdoptionStatus = Literal["PENDING", "PASSED", "OVERRIDDEN"]
AnnotatorHistoryTimeRange = Literal["7d", "30d"]


class ClaimReviewTaskRequest(BaseModel):
    reviewer_user_id: int
    count: int = Field(default=5, ge=1, le=1000)


class AnnotationAggregateCompetencyOut(BaseModel):
    competency_id: int
    competency_name: str
    level_value: int
    agreement_score: float | None = None


class AnnotationAggregateOut(BaseModel):
    id: int
    question_id: int
    final_cognitive_level_id: int | None = None
    agreement_score: float | None = None
    is_disputed: bool
    completed_annotation_count: int
    finalized_at: datetime | None = None
    competencies: list[AnnotationAggregateCompetencyOut]


class ReviewAnnotationCompetencyOut(BaseModel):
    competency_id: int
    competency_name: str
    level_value: int
    confidence_level: int = 5


class ReviewAnnotationOut(BaseModel):
    annotation_id: int
    user_id: int
    user_name: str
    cognitive_level_id: int | None = None
    confidence_level: int | None = None
    submitted_at: datetime
    competencies: list[ReviewAnnotationCompetencyOut]


class AnnotationConsensusVoteOut(BaseModel):
    level_value: int | None = None
    vote_count: int
    annotator_names: list[str]
    weighted_score: float | None = None


class AnnotationConsensusDimensionOut(BaseModel):
    dimension_type: Literal["cognitive_level", "competency"]
    dimension_key: str
    dimension_label: str
    recommended_level_value: int | None = None
    agreement_score: float
    consensus_status: Literal["UNANIMOUS", "MAJORITY", "DISPUTED"]
    decision_status: str | None = None
    reason_code: str | None = None
    vote_summary: list[AnnotationConsensusVoteOut]


class AnnotationConsensusSummaryOut(BaseModel):
    agreement_score: float | None = None
    consensus_status: Literal["UNANIMOUS", "MAJORITY", "DISPUTED", "INSUFFICIENT"]
    completed_annotation_count: int
    required_annotations: int
    unresolved_dimension_count: int
    dimensions: list[AnnotationConsensusDimensionOut]


class AnnotationReviewLogOut(BaseModel):
    id: int
    question_id: int
    aggregate_id: int | None = None
    review_task_id: int | None = None
    actor_user_id: int | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    action_code: str
    action_label: str
    comment: str | None = None
    detail_json: dict | None = None
    created_at: datetime


class ReviewTaskOut(BaseModel):
    id: int
    question_id: int
    aggregate_id: int
    reviewer_id: int | None = None
    review_status: str
    review_comment: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    question: QuestionListItem
    aggregate: AnnotationAggregateOut
    annotations: list[ReviewAnnotationOut]
    consensus: AnnotationConsensusSummaryOut
    review_logs: list[AnnotationReviewLogOut]


class ClaimReviewTaskResponse(BaseModel):
    claimed_count: int
    task_ids: list[int]
    items: list[ReviewTaskOut]


class AutoReconcileReviewTasksRequest(BaseModel):
    reviewer_user_id: int
    include_unclaimed: bool = True
    limit: int = Field(default=1000, ge=1, le=5000)


class AutoReconcileReviewTasksResponse(BaseModel):
    scanned_count: int
    auto_closed_count: int
    still_disputed_count: int
    skipped_insufficient_count: int
    auto_closed_question_ids: list[int]
    auto_closed_review_task_ids: list[int]
    still_disputed_question_ids: list[int]
    skipped_insufficient_question_ids: list[int]


class ReviewTaskListResponse(BaseModel):
    items: list[ReviewTaskOut]
    meta: PageMeta


class SubmitReviewTaskRequest(BaseModel):
    reviewer_user_id: int
    cognitive_level_id: int | None = None
    competencies: list[AnnotationCompetencyInput] = Field(default_factory=list)
    review_comment: str | None = None


class SubmitReviewTaskResponse(BaseModel):
    review_task_id: int
    question_id: int
    aggregate_id: int
    review_status: str
    question_status: AnnotationPoolStatus


class AdminQuestionAnnotationOut(BaseModel):
    annotation_id: int
    task_id: int | None = None
    task_status: str | None = None
    user_id: int
    user_name: str
    cognitive_level_id: int | None = None
    confidence_level: int | None = None
    submitted_at: datetime
    competencies: list[ReviewAnnotationCompetencyOut]


class AdminQuestionReviewOut(BaseModel):
    question_id: int
    annotation_status: AnnotationPoolStatus
    submitted_annotation_count: int
    active_annotation_count: int
    required_annotations: int
    remaining_annotation_count: int
    open_review_task_count: int
    aggregate: AnnotationAggregateOut | None = None
    gold_label: AnnotationAggregateOut | None = None
    consensus: AnnotationConsensusSummaryOut
    annotations: list[AdminQuestionAnnotationOut]
    review_logs: list[AnnotationReviewLogOut]


class AdminReviewDecisionRequest(BaseModel):
    admin_user_id: int
    review_comment: str | None = None
    additional_annotations: int = Field(default=1, ge=1, le=5)


class AdminAggregateOverrideRequest(BaseModel):
    admin_user_id: int
    final_cognitive_level_id: int | None = None
    competencies: list[AnnotationCompetencyInput] = Field(default_factory=list)
    review_comment: str | None = None
