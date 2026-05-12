from __future__ import annotations

import json
import math
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.models.assessment import EmbeddingModel, QuestionEmbedding
from app.models.question import Question


class EmbeddingUnavailableError(RuntimeError):
    """Raised when the local Roberta runtime cannot produce embeddings."""


@lru_cache(maxsize=1)
def _load_roberta_components(model_path: str):
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise EmbeddingUnavailableError(
            "Roberta embedding dependencies are not installed. "
            "Install backend dependencies again so torch and transformers are available."
        ) from exc

    path = Path(model_path)
    if not path.exists():
        raise EmbeddingUnavailableError(f"Embedding model path does not exist: {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModel.from_pretrained(str(path), local_files_only=True)
    model.eval()
    return tokenizer, model, torch


class EmbeddingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def get_embedding_status(self) -> dict[str, int | str | bool | None]:
        model = self.get_or_create_model()
        total_questions = self.db.scalar(select(func.count(Question.id))) or 0
        embedded_questions = (
            self.db.query(QuestionEmbedding.question_id)
            .filter(QuestionEmbedding.embedding_model_id == model.id)
            .distinct()
            .count()
        )
        return {
            "model_code": model.model_code,
            "model_name": model.model_name,
            "dimension": model.dimension,
            "model_path": self.settings.embedding_model_path,
            "model_available": self.is_model_available(),
            "total_questions": total_questions,
            "embedded_questions": embedded_questions,
            "missing_embeddings": max(total_questions - embedded_questions, 0),
        }

    def is_model_available(self) -> bool:
        model_path = Path(self.settings.embedding_model_path)
        return (
            model_path.exists()
            and (model_path / "config.json").exists()
            and find_spec("torch") is not None
            and find_spec("transformers") is not None
        )

    def get_or_create_model(self) -> EmbeddingModel:
        stmt = select(EmbeddingModel).where(
            EmbeddingModel.model_code == self.settings.embedding_model_code
        )
        model = self.db.scalar(stmt)
        if model is not None:
            return model

        model = EmbeddingModel(
            model_code=self.settings.embedding_model_code,
            model_name=self.settings.embedding_model_name,
            dimension=self._infer_dimension(),
            is_active=True,
        )
        self.db.add(model)
        self.db.flush()
        return model

    def ensure_question_embedding(self, question_id: int) -> QuestionEmbedding | None:
        question = self.db.scalar(
            select(Question)
            .options(selectinload(Question.content))
            .where(Question.id == question_id)
            .limit(1)
        )
        if question is None or question.content is None:
            return None

        model = self.get_or_create_model()
        existing = self._get_latest_embedding(question.id, model.id)
        if existing is not None:
            return existing

        vector = self.encode_questions([question])[0]
        return self._save_embedding(question, model, vector)

    def ensure_embeddings(self, question_ids: list[int]) -> dict[str, int]:
        created = 0
        skipped = 0
        failed = 0
        if not question_ids:
            return {"created": created, "skipped": skipped, "failed": failed}

        model = self.get_or_create_model()
        unique_question_ids = list(dict.fromkeys(question_ids))
        existing_ids = set(
            self.db.scalars(
                select(QuestionEmbedding.question_id).where(
                    QuestionEmbedding.embedding_model_id == model.id,
                    QuestionEmbedding.question_id.in_(unique_question_ids),
                )
            )
        )
        questions = list(
            self.db.scalars(
                select(Question)
                .options(selectinload(Question.content))
                .where(Question.id.in_(unique_question_ids))
            )
        )
        question_map = {question.id: question for question in questions}
        pending_questions: list[Question] = []
        for question_id in unique_question_ids:
            question = question_map.get(question_id)
            if question is None or question.content is None or question_id in existing_ids:
                skipped += 1
                continue
            pending_questions.append(question)

        batch_size = max(int(self.settings.embedding_batch_size or 16), 1)
        for start_index in range(0, len(pending_questions), batch_size):
            batch = pending_questions[start_index : start_index + batch_size]
            try:
                vectors = self.encode_questions(batch)
                for question, vector in zip(batch, vectors, strict=True):
                    self._save_embedding(question, model, vector)
                    created += 1
            except EmbeddingUnavailableError:
                raise
            except Exception:
                failed += len(batch)
        self.db.commit()
        return {"created": created, "skipped": skipped, "failed": failed}

    def rebuild_missing_embeddings(self, limit: int | None = None) -> dict[str, int]:
        model = self.get_or_create_model()
        embedded_question_ids = select(QuestionEmbedding.question_id).where(
            QuestionEmbedding.embedding_model_id == model.id
        )
        stmt = (
            select(Question.id)
            .where(~Question.id.in_(embedded_question_ids))
            .order_by(Question.id.asc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        question_ids = list(self.db.scalars(stmt))
        if not question_ids:
            return {"created": 0, "skipped": 0, "failed": 0}
        return self.ensure_embeddings(question_ids)

    def encode_question(self, question: Question) -> list[float]:
        return self.encode_questions([question])[0]

    def encode_questions(self, questions: list[Question]) -> list[list[float]]:
        if not questions:
            return []
        tokenizer, model, torch = _load_roberta_components(self.settings.embedding_model_path)
        texts = [self._question_text(question) for question in questions]
        encoded = tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )
        with torch.no_grad():
            output = model(**encoded)
            hidden = output.last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1e-9)
            vectors = pooled.detach().cpu().tolist()
        return [self._normalize(vector) for vector in vectors]

    def _save_embedding(
        self,
        question: Question,
        model: EmbeddingModel,
        vector: list[float],
    ) -> QuestionEmbedding:
        norm = math.sqrt(sum(value * value for value in vector))
        embedding = self._get_latest_embedding(question.id, model.id)
        if embedding is None:
            embedding = QuestionEmbedding(
                question_id=question.id,
                embedding_model_id=model.id,
                vector_json=vector,
                vector_norm=Decimal(str(round(norm, 6))),
                computed_at=datetime.utcnow(),
            )
            self.db.add(embedding)
        else:
            embedding.vector_json = vector
            embedding.vector_norm = Decimal(str(round(norm, 6)))
            embedding.computed_at = datetime.utcnow()
        question.latest_embedding_version = model.model_code
        self.db.flush()
        return embedding

    def _get_latest_embedding(
        self,
        question_id: int,
        embedding_model_id: int,
    ) -> QuestionEmbedding | None:
        stmt = (
            select(QuestionEmbedding)
            .where(
                QuestionEmbedding.question_id == question_id,
                QuestionEmbedding.embedding_model_id == embedding_model_id,
            )
            .order_by(QuestionEmbedding.computed_at.desc(), QuestionEmbedding.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def _infer_dimension(self) -> int:
        config_path = Path(self.settings.embedding_model_path) / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                hidden_size = int(config.get("hidden_size") or 0)
                if hidden_size > 0:
                    return hidden_size
            except Exception:
                pass
        return 768

    def _question_text(self, question: Question) -> str:
        content = question.content
        if content is None:
            return ""
        parts = [
            content.stem_text,
            content.answer_text,
            content.solution_text,
        ]
        return "\n".join(part.strip() for part in parts if part and part.strip())

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(float(value) * float(value) for value in vector))
        if norm <= 0:
            return [0.0 for _ in vector]
        return [round(float(value) / norm, 8) for value in vector]
