from __future__ import annotations

import hashlib
import math
import random
import re
from collections import Counter, OrderedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.assessment import (
    QuestionAggregateCompetency,
    QuestionEmbedding,
    QuestionGoldCompetency,
    QuestionGoldLabel,
    QuestionLabelAggregate,
)
from app.models.dictionary import CognitiveLevel, Competency, Grade
from app.models.question import Question, QuestionContent
from app.schemas.pagination import PageMeta
from app.schemas.visualization import (
    AnnotatedDistributionBucket,
    AnnotatedOverviewResponse,
    AnnotatedQuestionCompetencyOut,
    AnnotatedQuestionListItemOut,
    AnnotatedQuestionListResponse,
    DistributionPoint,
    QuestionDistributionResponse,
)
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

    def annotated_overview(self) -> AnnotatedOverviewResponse:
        records = self._load_labeled_records()
        return AnnotatedOverviewResponse(
            **self._build_labeled_overview(records),
        )

    def annotated_questions(
        self,
        *,
        keyword: str | None = None,
        subject_id: int | None = None,
        grade_id: int | None = None,
        edu_stage: str | None = None,
        question_type_id: int | None = None,
        result_source: str = "all",
        page: int = 1,
        page_size: int = 20,
    ) -> AnnotatedQuestionListResponse:
        records = self._load_labeled_records(
            keyword=keyword,
            subject_id=subject_id,
            grade_id=grade_id,
            edu_stage=edu_stage,
            question_type_id=question_type_id,
            result_source=result_source,
        )
        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        return AnnotatedQuestionListResponse(
            items=records[start:end],
            meta=PageMeta(page=page, page_size=page_size, total=total),
        )

    def annotated_filtered_overview(
        self,
        *,
        keyword: str | None = None,
        subject_id: int | None = None,
        grade_id: int | None = None,
        edu_stage: str | None = None,
        question_type_id: int | None = None,
        result_source: str = "all",
    ) -> AnnotatedOverviewResponse:
        total_records = self._load_labeled_records(result_source=result_source)
        records = self._load_labeled_records(
            keyword=keyword,
            subject_id=subject_id,
            grade_id=grade_id,
            edu_stage=edu_stage,
            question_type_id=question_type_id,
            result_source=result_source,
        )
        return AnnotatedOverviewResponse(
            **self._build_labeled_overview(records, total_count=len(total_records))
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

    def _serialize_annotated_question(
        self,
        result: dict,
    ) -> AnnotatedQuestionListItemOut:
        question = result["question"]
        competencies = result["competencies"]
        return AnnotatedQuestionListItemOut(
            question_id=question.id,
            stem_preview=self._preview(question),
            subject_name=question.subject.name,
            grade_name=question.grade.grade_name if question.grade is not None else None,
            edu_stage=question.grade.edu_stage if question.grade is not None else None,
            question_type_name=question.question_type.name if question.question_type is not None else None,
            annotation_status=question.annotation_status,
            result_source=result["result_source"],
            result_source_label=result["result_source_label"],
            final_cognitive_level_id=result["final_cognitive_level_id"],
            final_cognitive_level_name=result["final_cognitive_level_name"],
            agreement_score=result["agreement_score"],
            completed_annotation_count=result["completed_annotation_count"],
            finalized_at=result["finalized_at"],
            competencies=[
                AnnotatedQuestionCompetencyOut(
                    competency_id=item["competency_id"],
                    competency_name=item["competency_name"],
                    level_value=item["level_value"],
                    agreement_score=item["agreement_score"],
                )
                for item in competencies
            ],
        )

    def _load_labeled_records(
        self,
        *,
        keyword: str | None = None,
        subject_id: int | None = None,
        grade_id: int | None = None,
        edu_stage: str | None = None,
        question_type_id: int | None = None,
        result_source: str = "all",
    ) -> list[AnnotatedQuestionListItemOut]:
        aggregate_records: list[AnnotatedQuestionListItemOut] = []
        gold_records: list[AnnotatedQuestionListItemOut] = []
        aggregate_question_ids: set[int] = set()

        if result_source in {"all", "aggregate"}:
            aggregate_stmt = (
                select(QuestionLabelAggregate)
                .join(Question, Question.id == QuestionLabelAggregate.question_id)
                .options(
                    selectinload(QuestionLabelAggregate.question).selectinload(Question.subject),
                    selectinload(QuestionLabelAggregate.question).selectinload(Question.grade),
                    selectinload(QuestionLabelAggregate.question).selectinload(Question.question_type),
                    selectinload(QuestionLabelAggregate.question).selectinload(Question.content),
                    selectinload(QuestionLabelAggregate.final_cognitive_level),
                    selectinload(QuestionLabelAggregate.competencies).selectinload(
                        QuestionAggregateCompetency.competency
                    ),
                )
                .where(Question.annotation_status == "COMPLETED")
            )
            aggregate_stmt = self._apply_question_filters(
                aggregate_stmt,
                keyword=keyword,
                subject_id=subject_id,
                grade_id=grade_id,
                edu_stage=edu_stage,
                question_type_id=question_type_id,
            )
            aggregates = list(self.db.scalars(aggregate_stmt).unique())
            aggregate_question_ids = {item.question_id for item in aggregates}
            aggregate_records = [
                self._serialize_annotated_question(
                    {
                        "question": item.question,
                        "result_source": "aggregate",
                        "result_source_label": "最终标注",
                        "final_cognitive_level_id": item.final_cognitive_level_id,
                        "final_cognitive_level_name": item.final_cognitive_level.name
                        if item.final_cognitive_level is not None
                        else None,
                        "agreement_score": float(item.agreement_score)
                        if item.agreement_score is not None
                        else None,
                        "completed_annotation_count": item.completed_annotation_count,
                        "finalized_at": item.finalized_at,
                        "competencies": [
                            {
                                "competency_id": competency.competency_id,
                                "competency_name": competency.competency.name
                                if competency.competency is not None
                                else str(competency.competency_id),
                                "level_value": competency.level_value,
                                "agreement_score": float(competency.agreement_score)
                                if competency.agreement_score is not None
                                else None,
                            }
                            for competency in item.competencies
                        ],
                    }
                )
                for item in aggregates
            ]

        if result_source in {"all", "gold"}:
            gold_stmt = (
                select(QuestionGoldLabel)
                .join(Question, Question.id == QuestionGoldLabel.question_id)
                .options(
                    selectinload(QuestionGoldLabel.question).selectinload(Question.subject),
                    selectinload(QuestionGoldLabel.question).selectinload(Question.grade),
                    selectinload(QuestionGoldLabel.question).selectinload(Question.question_type),
                    selectinload(QuestionGoldLabel.question).selectinload(Question.content),
                    selectinload(QuestionGoldLabel.cognitive_level),
                    selectinload(QuestionGoldLabel.competencies).selectinload(
                        QuestionGoldCompetency.competency
                    ),
                )
            )
            if aggregate_question_ids:
                gold_stmt = gold_stmt.where(~QuestionGoldLabel.question_id.in_(aggregate_question_ids))
            gold_stmt = self._apply_question_filters(
                gold_stmt,
                keyword=keyword,
                subject_id=subject_id,
                grade_id=grade_id,
                edu_stage=edu_stage,
                question_type_id=question_type_id,
            )
            golds = list(self.db.scalars(gold_stmt).unique())
            gold_records = [
                self._serialize_annotated_question(
                    {
                        "question": item.question,
                        "result_source": "gold",
                        "result_source_label": "金标",
                        "final_cognitive_level_id": item.cognitive_level_id,
                        "final_cognitive_level_name": item.cognitive_level.name
                        if item.cognitive_level is not None
                        else None,
                        "agreement_score": None,
                        "completed_annotation_count": 1,
                        "finalized_at": item.imported_at,
                        "competencies": [
                            {
                                "competency_id": competency.competency_id,
                                "competency_name": competency.competency.name
                                if competency.competency is not None
                                else str(competency.competency_id),
                                "level_value": competency.level_value,
                                "agreement_score": None,
                            }
                            for competency in item.competencies
                        ],
                    }
                )
                for item in golds
            ]

        combined = aggregate_records + gold_records
        combined.sort(
            key=lambda item: (
                item.finalized_at.isoformat() if item.finalized_at is not None else "",
                item.question_id,
            ),
            reverse=True,
        )
        return combined

    def _build_labeled_overview(
        self,
        records: list[AnnotatedQuestionListItemOut],
        total_count: int | None = None,
    ) -> dict:
        cognitive_counter: Counter[tuple[str, str]] = Counter()
        competency_counter: Counter[tuple[str, str]] = Counter()
        competency_level_counter: Counter[tuple[str, str]] = Counter()
        grade_counter: Counter[tuple[str, str]] = Counter()
        aggregate_scores: list[float] = []
        gold_count = 0
        aggregate_count = 0

        for record in records:
            if record.final_cognitive_level_name:
                cognitive_counter[(str(record.final_cognitive_level_id), record.final_cognitive_level_name)] += 1
            if record.grade_name:
                grade_counter[(record.grade_name, record.grade_name)] += 1
            if record.result_source == "gold":
                gold_count += 1
            else:
                aggregate_count += 1
                if record.agreement_score is not None:
                    aggregate_scores.append(record.agreement_score)
            for competency in record.competencies:
                if competency.level_value <= 0:
                    continue
                competency_counter[(str(competency.competency_id), competency.competency_name)] += 1
                competency_level_counter[
                    (
                        f"{competency.competency_id}_L{competency.level_value}",
                        f"{competency.competency_name} L{competency.level_value}",
                    )
                ] += 1

        average_agreement_score = (
            round(sum(aggregate_scores) / len(aggregate_scores), 2) if aggregate_scores else None
        )
        return {
            "total_labeled_questions": total_count if total_count is not None else len(records),
            "filtered_question_count": len(records),
            "gold_labeled_questions": gold_count,
            "aggregate_labeled_questions": aggregate_count,
            "total_completed_questions": len(records),
            "disputed_questions": 0,
            "average_agreement_score": average_agreement_score,
            "cognitive_level_distribution": [
                AnnotatedDistributionBucket(key=key, label=label, count=count)
                for (key, label), count in cognitive_counter.most_common()
            ],
            "competency_distribution": [
                AnnotatedDistributionBucket(key=key, label=label, count=count)
                for (key, label), count in competency_counter.most_common()
            ],
            "competency_level_distribution": [
                AnnotatedDistributionBucket(key=key, label=label, count=count)
                for (key, label), count in competency_level_counter.most_common()
            ],
            "grade_distribution": [
                AnnotatedDistributionBucket(key=key, label=label, count=count)
                for (key, label), count in grade_counter.most_common()
            ],
        }

    def _apply_question_filters(
        self,
        stmt,
        *,
        keyword: str | None = None,
        subject_id: int | None = None,
        grade_id: int | None = None,
        edu_stage: str | None = None,
        question_type_id: int | None = None,
    ):
        if keyword:
            stmt = stmt.join(QuestionContent, QuestionContent.question_id == Question.id).where(
                QuestionContent.stem_text.contains(keyword.strip())
            )
        if subject_id is not None:
            stmt = stmt.where(Question.subject_id == subject_id)
        if grade_id is not None:
            stmt = stmt.where(Question.grade_id == grade_id)
        if edu_stage is not None:
            stmt = stmt.join(Grade, Grade.id == Question.grade_id).where(Grade.edu_stage == edu_stage)
        if question_type_id is not None:
            stmt = stmt.where(Question.question_type_id == question_type_id)
        return stmt
