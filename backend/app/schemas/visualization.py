from __future__ import annotations

from pydantic import BaseModel


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
