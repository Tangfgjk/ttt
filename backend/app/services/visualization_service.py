from __future__ import annotations

import hashlib
import math
import random
import re
from collections import Counter, OrderedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.assessment import QuestionEmbedding
from app.models.question import Question, QuestionContent
from app.schemas.visualization import DistributionPoint, QuestionDistributionResponse
from app.services.embedding_service import EmbeddingService

_DISTRIBUTION_CACHE_LIMIT = 12
_DISTRIBUTION_CACHE: OrderedDict[str, QuestionDistributionResponse] = OrderedDict()


class VisualizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.embedding_service = EmbeddingService(db)

    def question_distribution(
        self,
        *,
        method: str = "pca",
        status_filter: str = "all",
        limit: int | None = None,
    ) -> QuestionDistributionResponse:
        model = self.embedding_service.get_or_create_model()
        summary = self._status_summary()
        effective_limit = min(limit or self.settings.visualization_max_points, self.settings.visualization_max_points)
        cache_key = self._distribution_cache_key(
            model_id=model.id,
            method=method,
            status_filter=status_filter,
            limit=effective_limit,
            summary=summary,
        )
        cached = _DISTRIBUTION_CACHE.get(cache_key)
        if cached is not None:
            _DISTRIBUTION_CACHE.move_to_end(cache_key)
            return cached

        rows = self._embedding_rows(model.id, status_filter=status_filter, limit=effective_limit)
        vectors = [row["vector"] for row in rows]
        projection, actual_method = self._project(vectors, method)
        points = [
            DistributionPoint(
                question_id=row["question"].id,
                x=round(float(projection[index][0]), 6),
                y=round(float(projection[index][1]), 6),
                annotation_status=row["question"].annotation_status,
                annotation_count=row["question"].annotation_count,
                required_annotations=row["question"].required_annotations,
                stem_preview=self._preview(row["question"]),
            )
            for index, row in enumerate(rows)
        ]
        total_questions = sum(summary.values())
        return self._remember_distribution_cache(
            cache_key,
            QuestionDistributionResponse(
            method=actual_method,
            requested_method=method,
            model_code=model.model_code,
            embedding_count=len(points),
            missing_embedding_count=max(
                total_questions - self._embedded_question_count(model.id),
                0,
            ),
            summary=summary,
            points=points,
            ),
        )

    def _distribution_cache_key(
        self,
        *,
        model_id: int,
        method: str,
        status_filter: str,
        limit: int,
        summary: dict[str, int],
    ) -> str:
        embedding_updated_at = self.db.scalar(
            select(func.max(QuestionEmbedding.computed_at)).where(
                QuestionEmbedding.embedding_model_id == model_id
            )
        )
        question_updated_at = self.db.scalar(select(func.max(Question.updated_at)))
        content_updated_at = self.db.scalar(select(func.max(QuestionContent.updated_at)))
        payload = "|".join(
            [
                f"model={model_id}",
                f"method={method}",
                f"status={status_filter}",
                f"limit={limit}",
                f"summary={sorted(summary.items())}",
                f"embedding_updated_at={embedding_updated_at.isoformat() if embedding_updated_at else ''}",
                f"question_updated_at={question_updated_at.isoformat() if question_updated_at else ''}",
                f"content_updated_at={content_updated_at.isoformat() if content_updated_at else ''}",
            ]
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def _remember_distribution_cache(
        self,
        cache_key: str,
        response: QuestionDistributionResponse,
    ) -> QuestionDistributionResponse:
        _DISTRIBUTION_CACHE[cache_key] = response
        _DISTRIBUTION_CACHE.move_to_end(cache_key)
        while len(_DISTRIBUTION_CACHE) > _DISTRIBUTION_CACHE_LIMIT:
            _DISTRIBUTION_CACHE.popitem(last=False)
        return response

    def _embedding_rows(
        self,
        model_id: int,
        *,
        status_filter: str,
        limit: int | None,
    ) -> list[dict]:
        stmt = (
            select(Question, QuestionEmbedding)
            .join(QuestionEmbedding, QuestionEmbedding.question_id == Question.id)
            .options(selectinload(Question.content))
            .where(QuestionEmbedding.embedding_model_id == model_id)
            .order_by(Question.id.asc(), QuestionEmbedding.computed_at.desc())
        )
        if status_filter and status_filter.lower() != "all":
            stmt = stmt.where(Question.annotation_status == status_filter)

        max_points = self.settings.visualization_max_points
        effective_limit = min(limit or max_points, max_points)
        stmt = stmt.limit(effective_limit * 2)

        rows: list[dict] = []
        seen_question_ids: set[int] = set()
        for question, embedding in self.db.execute(stmt).all():
            if question.id in seen_question_ids:
                continue
            seen_question_ids.add(question.id)
            rows.append(
                {
                    "question": question,
                    "vector": [float(value) for value in embedding.vector_json],
                }
            )
            if len(rows) >= effective_limit:
                break
        return rows

    def _project(
        self,
        vectors: list[list[float]],
        method: str,
    ) -> tuple[list[tuple[float, float]], str]:
        if not vectors:
            return [], method
        if len(vectors) == 1:
            return [(0.0, 0.0)], method

        normalized_method = method.lower()
        if normalized_method == "tsne" and len(vectors) <= 5000:
            projected = self._project_tsne(vectors)
            if projected is not None:
                return projected, "tsne"
        if normalized_method == "umap":
            projected = self._project_umap(vectors)
            if projected is not None:
                return projected, "umap"

        projected = self._project_pca(vectors)
        if projected is not None:
            return projected, "pca"
        return self._project_random(vectors), "random_projection"

    def _project_pca(self, vectors: list[list[float]]) -> list[tuple[float, float]] | None:
        try:
            import numpy as np
            from sklearn.decomposition import PCA

            matrix = np.asarray(vectors, dtype=float)
            coords = PCA(
                n_components=2,
                svd_solver="randomized",
                random_state=42,
            ).fit_transform(matrix)
            return [(float(item[0]), float(item[1])) for item in coords]
        except Exception:
            return None

    def _project_tsne(self, vectors: list[list[float]]) -> list[tuple[float, float]] | None:
        try:
            import numpy as np
            from sklearn.manifold import TSNE

            matrix = np.asarray(vectors, dtype=float)
            perplexity = min(30, max(5, len(vectors) // 10))
            coords = TSNE(
                n_components=2,
                random_state=42,
                init="pca",
                learning_rate="auto",
                perplexity=perplexity,
            ).fit_transform(matrix)
            return [(float(item[0]), float(item[1])) for item in coords]
        except Exception:
            return None

    def _project_umap(self, vectors: list[list[float]]) -> list[tuple[float, float]] | None:
        try:
            import numpy as np
            import umap

            matrix = np.asarray(vectors, dtype=float)
            coords = umap.UMAP(n_components=2, random_state=42).fit_transform(matrix)
            return [(float(item[0]), float(item[1])) for item in coords]
        except Exception:
            return None

    def _project_random(self, vectors: list[list[float]]) -> list[tuple[float, float]]:
        dimension = len(vectors[0])
        rng = random.Random(42)
        weights_x = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
        weights_y = [rng.uniform(-1.0, 1.0) for _ in range(dimension)]
        scale = math.sqrt(max(dimension, 1))
        return [
            (
                sum(value * weights_x[index] for index, value in enumerate(vector)) / scale,
                sum(value * weights_y[index] for index, value in enumerate(vector)) / scale,
            )
            for vector in vectors
        ]

    def _status_summary(self) -> dict[str, int]:
        statuses = list(self.db.scalars(select(Question.annotation_status)))
        return dict(Counter(statuses))

    def _embedded_question_count(self, model_id: int) -> int:
        return (
            self.db.query(QuestionEmbedding.question_id)
            .filter(QuestionEmbedding.embedding_model_id == model_id)
            .distinct()
            .count()
        )

    def _preview(self, question: Question) -> str:
        if question.content is None:
            return ""
        text = question.content.stem_text or question.content.stem_html or ""
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            fingerprint = hashlib.sha1(str(question.id).encode("utf-8")).hexdigest()[:8]
            return f"Question {fingerprint}"
        return text[:120]
