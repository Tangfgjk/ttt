from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.pagination import PageMeta


class EmbeddingStatusResponse(BaseModel):
    model_code: str
    model_name: str
    dimension: int
    model_path: str
    model_available: bool
    total_questions: int
    embedded_questions: int
    missing_embeddings: int


class EmbeddingRebuildRequest(BaseModel):
    limit: int | None = None


class EmbeddingRebuildResponse(BaseModel):
    created: int
    skipped: int
    failed: int


class DistributionPoint(BaseModel):
    question_id: int
    x: float
    y: float
    annotation_status: str
    annotation_count: int
    required_annotations: int
    stem_preview: str


class QuestionDistributionResponse(BaseModel):
    method: str
    requested_method: str
    model_code: str
    embedding_count: int
    missing_embedding_count: int
    summary: dict[str, int]
    points: list[DistributionPoint]


class AnnotatedDistributionBucket(BaseModel):
    key: str
    label: str
    count: int


class AnnotatedOverviewResponse(BaseModel):
    total_labeled_questions: int
    filtered_question_count: int
    gold_labeled_questions: int
    aggregate_labeled_questions: int
    total_completed_questions: int
    disputed_questions: int
    average_agreement_score: float | None = None
    cognitive_level_distribution: list[AnnotatedDistributionBucket]
    competency_distribution: list[AnnotatedDistributionBucket]
    competency_level_distribution: list[AnnotatedDistributionBucket]
    grade_distribution: list[AnnotatedDistributionBucket]


class AnnotatedQuestionCompetencyOut(BaseModel):
    competency_id: int
    competency_name: str
    level_value: int
    agreement_score: float | None = None


class AnnotatedQuestionListItemOut(BaseModel):
    question_id: int
    stem_preview: str
    subject_name: str
    grade_name: str | None = None
    edu_stage: str | None = None
    question_type_name: str | None = None
    annotation_status: str
    result_source: str
    result_source_label: str
    final_cognitive_level_id: int | None = None
    final_cognitive_level_name: str | None = None
    agreement_score: float | None = None
    completed_annotation_count: int
    finalized_at: datetime | None = None
    competencies: list[AnnotatedQuestionCompetencyOut]


class AnnotatedQuestionListResponse(BaseModel):
    items: list[AnnotatedQuestionListItemOut]
    meta: PageMeta
