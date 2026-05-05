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


class PoolSummaryItem(BaseModel):
    status: AnnotationPoolStatus
    count: int


class PoolSummaryResponse(BaseModel):
    items: list[PoolSummaryItem]


class SelectionStrategyItem(BaseModel):
    code: SelectionStrategy
    name: str
    description: str


class AdminSelectionRequest(BaseModel):
    strategy: SelectionStrategy = "moe"
    count: int = Field(default=100, ge=100, le=1000)
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


class ClaimAnnotationRequest(BaseModel):
    annotator_user_id: int
    count: int = Field(default=10, ge=10, le=100)


class ClaimAnnotationResponse(BaseModel):
    claimed_count: int
    task_ids: list[int]
    items: list["AnnotationTaskOut"]


class AnnotationCompetencyInput(BaseModel):
    competency_id: int
    level_value: int = Field(ge=0, le=3)


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


class AnnotationTaskListResponse(BaseModel):
    items: list[AnnotationTaskOut]
    meta: PageMeta


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
