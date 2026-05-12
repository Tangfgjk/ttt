from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.visualization import (
    EmbeddingRebuildRequest,
    EmbeddingRebuildResponse,
    EmbeddingStatusResponse,
    QuestionDistributionResponse,
)
from app.services.embedding_service import EmbeddingService, EmbeddingUnavailableError
from app.services.visualization_service import VisualizationService

router = APIRouter()


@router.get("/embedding-status", response_model=EmbeddingStatusResponse)
async def get_embedding_status(db: Session = Depends(get_db)) -> EmbeddingStatusResponse:
    return EmbeddingStatusResponse(**EmbeddingService(db).get_embedding_status())


@router.post("/embeddings/rebuild", response_model=EmbeddingRebuildResponse)
async def rebuild_embeddings(
    payload: EmbeddingRebuildRequest,
    db: Session = Depends(get_db),
) -> EmbeddingRebuildResponse:
    try:
        result = EmbeddingService(db).rebuild_missing_embeddings(limit=payload.limit)
    except EmbeddingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return EmbeddingRebuildResponse(**result)


@router.get("/question-distribution", response_model=QuestionDistributionResponse)
async def get_question_distribution(
    method: str = Query(default="pca", pattern="^(pca|tsne|umap)$"),
    status_filter: str = Query(default="all", alias="status"),
    limit: int | None = Query(default=None, ge=1, le=50000),
    db: Session = Depends(get_db),
) -> QuestionDistributionResponse:
    return VisualizationService(db).question_distribution(
        method=method,
        status_filter=status_filter,
        limit=limit,
    )
