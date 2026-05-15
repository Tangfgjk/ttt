from __future__ import annotations

import copy
import math
import os
import random
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.assessment import (
    CoresetExperiment,
    EmbeddingModel,
    ModelCoresetRun,
    ModelPredictionItem,
    ModelPredictionRun,
    ModelTrainingEpoch,
    ModelTrainingRun,
    ModelVersion,
    QuestionEmbedding,
    QuestionAggregateCompetency,
    QuestionGoldCompetency,
    QuestionGoldLabel,
    QuestionLabelAggregate,
    RecommendationBatch,
    RecommendationItem,
)
from app.models.auth import User
from app.models.dictionary import Competency, Grade
from app.models.question import Question, QuestionContent
from app.schemas.active_learning import (
    ActiveLearningOverviewResponse,
    CoresetIncrementalSummaryOut,
    CoresetRunCreateRequest,
    CoresetRunOut,
    ModelVersionOut,
    PredictionItemOut,
    PredictionRunCreateRequest,
    PredictionRunOut,
    TrendGroupOut,
    TrendPointOut,
    TrainingRunLogOut,
    TrainingEpochOut,
    TrainingRunCreateRequest,
    TrainingRunOut,
)
from app.services.coreset_selection import CoresetCandidate, CoresetSelector
from app.services.embedding_service import EmbeddingService
from app.services.training_service import STAGE_COMPETENCY_CODES

QUESTION_STATUS_PENDING = "PENDING"
QUESTION_STATUS_WAITING = "WAITING"
QUESTION_STATUS_COMPLETED = "COMPLETED"
QUESTION_SOURCE_ACTIVE = "ACTIVE"

RUN_STATUS_PENDING = "PENDING"
RUN_STATUS_RUNNING = "RUNNING"
RUN_STATUS_SUCCESS = "SUCCESS"
RUN_STATUS_FAILED = "FAILED"

NUM_LEVELS = 4
LOG_TAIL_BYTES = 64 * 1024


@dataclass(frozen=True)
class TrainingExample:
    question_id: int
    text: str
    labels: list[int]


@dataclass(frozen=True)
class PredictionCandidate:
    question_id: int
    text: str


class ActiveLearningService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def overview(self) -> ActiveLearningOverviewResponse:
        model_versions = self._model_versions()
        training_runs = self._training_runs()
        return ActiveLearningOverviewResponse(
            active_model=self._active_model_version_out(),
            model_versions=[self._model_version_out(item) for item in model_versions],
            training_runs=[self._training_run_out(item) for item in training_runs],
            prediction_runs=[self._prediction_run_out(item) for item in self._prediction_runs()],
            coreset_runs=[self._coreset_run_out(item) for item in self._coreset_runs()],
            coreset_incremental=self._coreset_incremental_summary(),
            trend_groups=self._trend_groups_out(model_versions),
            completed_sample_count=self._completed_sample_count(),
            pending_candidate_count=self._pending_candidate_count(),
        )

    def start_training_run(self, payload: TrainingRunCreateRequest) -> TrainingRunOut:
        self._ensure_user_exists(payload.triggered_by_user_id, required=False)
        run = ModelTrainingRun(
            run_no=f"train_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            status=RUN_STATUS_PENDING,
            triggered_by_user_id=payload.triggered_by_user_id,
            base_model_path=self.settings.embedding_model_path,
            target_stage=payload.target_stage,
            params_json=payload.model_dump(),
            created_at=datetime.utcnow(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        try:
            _spawn_active_learning_worker(
                "training",
                run.id,
                python_executable=_resolve_worker_python_for_device(payload.device),
            )
        except OSError as exc:
            run.status = RUN_STATUS_FAILED
            run.error_message = f"Failed to start training worker: {exc}"
            run.finished_at = datetime.utcnow()
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="鍚姩璁粌杩涚▼澶辫触",
            ) from exc
        return self.get_training_run(run.id)

    def get_training_run(self, run_id: int) -> TrainingRunOut:
        run = self.db.scalar(
            select(ModelTrainingRun)
            .options(
                selectinload(ModelTrainingRun.epochs),
                selectinload(ModelTrainingRun.model_versions),
            )
            .where(ModelTrainingRun.id == run_id)
        )
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training run not found")
        return self._training_run_out(run)

    def get_training_run_logs(self, run_id: int) -> TrainingRunLogOut:
        run = self.db.get(ModelTrainingRun, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training run not found")
        log_text, log_truncated = _tail_text(_training_run_log_path(run_id), LOG_TAIL_BYTES)
        stderr_text, stderr_truncated = _tail_text(_training_stderr_log_path(), LOG_TAIL_BYTES // 2)
        return TrainingRunLogOut(
            run_id=run_id,
            log_text=log_text,
            stderr_text=stderr_text,
            is_truncated=log_truncated or stderr_truncated,
        )

    def cancel_training_run(self, run_id: int) -> TrainingRunOut:
        run = self.db.get(ModelTrainingRun, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training run not found")
        if run.status not in {RUN_STATUS_PENDING, RUN_STATUS_RUNNING}:
            return self.get_training_run(run_id)

        logger = _RunLogger(run_id)
        terminated = _terminate_training_worker(run_id)
        run.status = RUN_STATUS_FAILED
        run.error_message = "Training run was cancelled by user."
        run.finished_at = datetime.utcnow()
        self.db.commit()
        logger.write(
            "Training run cancelled by user. "
            f"worker_terminated={terminated}."
        )
        return self.get_training_run(run_id)

    def list_training_runs(self) -> list[TrainingRunOut]:
        return [self._training_run_out(item) for item in self._training_runs()]

    def list_model_versions(self) -> list[ModelVersionOut]:
        return [self._model_version_out(item) for item in self._model_versions()]

    def activate_model_version(self, model_version_id: int) -> ModelVersionOut:
        version = self.db.get(ModelVersion, model_version_id)
        if version is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found")
        for item in self.db.scalars(select(ModelVersion).where(ModelVersion.is_active.is_(True))):
            item.is_active = False
        version.is_active = True
        self.db.commit()
        self.db.refresh(version)
        return self._model_version_out(version)

    def start_prediction_run(self, payload: PredictionRunCreateRequest) -> PredictionRunOut:
        self._ensure_user_exists(payload.triggered_by_user_id, required=False)
        active_run = self.db.scalar(
            select(ModelPredictionRun)
            .where(ModelPredictionRun.status.in_([RUN_STATUS_PENDING, RUN_STATUS_RUNNING]))
            .order_by(ModelPredictionRun.created_at.desc(), ModelPredictionRun.id.desc())
            .limit(1)
        )
        if active_run is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Prediction run {active_run.run_no} is already active.",
            )
        model_version = self._resolve_model_version(payload.model_version_id)
        run = ModelPredictionRun(
            run_no=f"predict_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            model_version_id=model_version.id,
            status=RUN_STATUS_PENDING,
            triggered_by_user_id=payload.triggered_by_user_id,
            confidence_strategy=payload.confidence_strategy,
            params_json=payload.model_dump(),
            created_at=datetime.utcnow(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        try:
            _spawn_active_learning_worker(
                "prediction",
                run.id,
                python_executable=_resolve_worker_python_for_device("auto"),
            )
        except OSError as exc:
            run.status = RUN_STATUS_FAILED
            run.error_message = f"Failed to start prediction worker: {exc}"
            run.finished_at = datetime.utcnow()
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="鍚姩棰勬祴杩涚▼澶辫触",
            ) from exc
        return self.get_prediction_run(run.id)

    def cancel_prediction_run(self, run_id: int) -> PredictionRunOut:
        run = self.db.get(ModelPredictionRun, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction run not found")
        if run.status not in {RUN_STATUS_PENDING, RUN_STATUS_RUNNING}:
            return self.get_prediction_run(run_id)

        terminated = _terminate_prediction_worker(run_id)
        run.status = RUN_STATUS_FAILED
        run.error_message = "Prediction run was cancelled by user."
        run.finished_at = datetime.utcnow()
        self.db.commit()
        return self.get_prediction_run(run_id)

    def start_coreset_run(self, payload: CoresetRunCreateRequest) -> CoresetRunOut:
        self._ensure_user_exists(payload.triggered_by_user_id, required=False)
        active_run = self.db.scalar(
            select(ModelCoresetRun)
            .where(ModelCoresetRun.status.in_([RUN_STATUS_PENDING, RUN_STATUS_RUNNING]))
            .order_by(ModelCoresetRun.created_at.desc(), ModelCoresetRun.id.desc())
            .limit(1)
        )
        if active_run is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Coreset run {active_run.run_no} is already active.",
            )

        baseline_run = None
        if payload.update_mode == "incremental":
            baseline_run = self._resolve_incremental_baseline(payload.data_scope)
            if baseline_run is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No successful CoreSet baseline exists yet. Please run a full-pool CoreSet first.",
                )

        params_json = payload.model_dump()
        if baseline_run is not None:
            params_json["baseline_run_id"] = baseline_run.id

        run = ModelCoresetRun(
            run_no=f"coreset_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
            status=RUN_STATUS_PENDING,
            triggered_by_user_id=payload.triggered_by_user_id,
            strategy=payload.strategy,
            data_scope=payload.data_scope,
            requested_count=payload.count,
            candidate_count=0,
            selected_count=0,
            moved_count=0,
            params_json=params_json,
            metrics_json={
                "progress_percent": 0,
                "progress_label": "等待执行",
                "phase": "queued",
                "selection_mode": _default_coreset_selection_mode(payload.strategy),
                "update_mode": payload.update_mode,
                "baseline_run_id": baseline_run.id if baseline_run else None,
                "baseline_run_no": baseline_run.run_no if baseline_run else None,
                "baseline_batch_no": baseline_run.recommendation_batch.batch_no
                if baseline_run and baseline_run.recommendation_batch
                else None,
                "snapshot_created_before": _snapshot_cutoff_from_run(baseline_run).isoformat()
                if baseline_run is not None and _snapshot_cutoff_from_run(baseline_run)
                else None,
            },
            created_at=datetime.utcnow(),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        try:
            _spawn_active_learning_worker(
                "coreset",
                run.id,
                python_executable=_resolve_worker_python_for_device("cpu"),
            )
        except OSError as exc:
            run.status = RUN_STATUS_FAILED
            run.error_message = f"Failed to start coreset worker: {exc}"
            run.finished_at = datetime.utcnow()
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="启动 CoreSet 进程失败",
            ) from exc
        return self.get_coreset_run(run.id)

    def list_coreset_runs(self) -> list[CoresetRunOut]:
        return [self._coreset_run_out(item) for item in self._coreset_runs()]

    def get_coreset_run(self, run_id: int) -> CoresetRunOut:
        run = self.db.scalar(
            select(ModelCoresetRun)
            .options(
                selectinload(ModelCoresetRun.recommendation_batch).selectinload(
                    RecommendationBatch.items
                )
            )
            .where(ModelCoresetRun.id == run_id)
        )
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coreset run not found")
        return self._coreset_run_out(run)

    def cancel_coreset_run(self, run_id: int) -> CoresetRunOut:
        run = self.db.get(ModelCoresetRun, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coreset run not found")
        if run.status not in {RUN_STATUS_PENDING, RUN_STATUS_RUNNING}:
            return self.get_coreset_run(run_id)

        terminated = _terminate_coreset_worker(run_id)
        run.status = RUN_STATUS_FAILED
        run.error_message = "Coreset run was cancelled by user."
        run.finished_at = datetime.utcnow()
        run.metrics_json = {
            **(run.metrics_json or {}),
            "progress_percent": 0,
            "progress_label": "已取消",
            "worker_terminated": terminated,
        }
        self.db.commit()
        return self.get_coreset_run(run_id)

    def get_prediction_run(self, run_id: int, *, include_items: bool = True) -> PredictionRunOut:
        options = []
        if include_items:
            options.append(selectinload(ModelPredictionRun.items))
        run = self.db.scalar(
            select(ModelPredictionRun).options(*options).where(ModelPredictionRun.id == run_id)
        )
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction run not found")
        return self._prediction_run_out(run, include_items=include_items)

    def list_prediction_runs(self) -> list[PredictionRunOut]:
        return [self._prediction_run_out(item) for item in self._prediction_runs()]

    def _resolve_model_version(self, model_version_id: int | None) -> ModelVersion:
        stmt = select(ModelVersion)
        if model_version_id is None:
            stmt = (
                stmt.where(ModelVersion.is_active.is_(True))
                .where(ModelVersion.training_run_id.is_not(None))
                .where(ModelVersion.checkpoint_path.is_not(None))
                .order_by(ModelVersion.created_at.desc())
            )
        else:
            stmt = (
                stmt.where(ModelVersion.id == model_version_id)
                .where(ModelVersion.training_run_id.is_not(None))
                .where(ModelVersion.checkpoint_path.is_not(None))
            )
        version = self.db.scalar(stmt.limit(1))
        if version is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No available model version")
        return version

    def _ensure_user_exists(self, user_id: int | None, *, required: bool = True) -> None:
        if user_id is None and not required:
            return
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="缂哄皯鐢ㄦ埛 ID",
            )
        exists = self.db.scalar(select(User.id).where(User.id == user_id))
        if exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    def _training_runs(self) -> list[ModelTrainingRun]:
        return list(
            self.db.scalars(
                select(ModelTrainingRun)
                .options(
                    selectinload(ModelTrainingRun.epochs),
                    selectinload(ModelTrainingRun.model_versions),
                )
                .order_by(ModelTrainingRun.created_at.desc(), ModelTrainingRun.id.desc())
                .limit(20)
            ).unique()
        )

    def _prediction_runs(self) -> list[ModelPredictionRun]:
        return list(
            self.db.scalars(
                select(ModelPredictionRun)
                .order_by(ModelPredictionRun.created_at.desc(), ModelPredictionRun.id.desc())
                .limit(20)
            )
        )

    def _coreset_runs(self) -> list[ModelCoresetRun]:
        return list(
            self.db.scalars(
                select(ModelCoresetRun)
                .options(
                    selectinload(ModelCoresetRun.recommendation_batch).selectinload(
                        RecommendationBatch.items
                    )
                )
                .order_by(ModelCoresetRun.created_at.desc(), ModelCoresetRun.id.desc())
                .limit(20)
            ).unique()
        )

    def _resolve_incremental_baseline(
        self,
        data_scope: str,
    ) -> ModelCoresetRun | None:
        return self.db.scalar(
            select(ModelCoresetRun)
            .options(selectinload(ModelCoresetRun.recommendation_batch))
            .where(ModelCoresetRun.status == RUN_STATUS_SUCCESS)
            .where(ModelCoresetRun.data_scope == data_scope)
            .where(ModelCoresetRun.recommendation_batch_id.is_not(None))
            .order_by(ModelCoresetRun.finished_at.desc(), ModelCoresetRun.id.desc())
            .limit(1)
        )

    def _coreset_incremental_summary(self) -> CoresetIncrementalSummaryOut | None:
        baseline_run = self._resolve_incremental_baseline("pending")
        if baseline_run is None:
            return CoresetIncrementalSummaryOut(can_run_incremental=False, data_scope="pending")

        cutoff = _snapshot_cutoff_from_run(baseline_run)
        incremental_candidate_count = self._count_incremental_candidates(
            data_scope="pending",
            created_after=cutoff,
        )
        anchor_count = self._count_incremental_anchor_questions(
            data_scope="pending",
            up_to_created_at=baseline_run.created_at,
        )
        return CoresetIncrementalSummaryOut(
            can_run_incremental=True,
            data_scope="pending",
            baseline_run_id=baseline_run.id,
            baseline_run_no=baseline_run.run_no,
            baseline_batch_no=baseline_run.recommendation_batch.batch_no
            if baseline_run.recommendation_batch
            else None,
            baseline_strategy=baseline_run.strategy,
            baseline_finished_at=baseline_run.finished_at,
            baseline_selected_count=baseline_run.selected_count,
            incremental_candidate_count=incremental_candidate_count,
            anchor_count=anchor_count,
            snapshot_created_before=cutoff,
        )

    def _count_incremental_candidates(
        self,
        *,
        data_scope: str,
        created_after: datetime | None,
    ) -> int:
        stmt = (
            select(func.count(Question.id))
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .where(Question.source_status == QUESTION_SOURCE_ACTIVE)
            .where(QuestionContent.stem_text != "")
        )
        if data_scope == "pending":
            stmt = stmt.where(Question.annotation_status == QUESTION_STATUS_PENDING)
        if created_after is not None:
            stmt = stmt.where(Question.created_at > created_after)
        return int(self.db.scalar(stmt) or 0)

    def _count_incremental_anchor_questions(
        self,
        *,
        data_scope: str,
        up_to_created_at: datetime | None,
    ) -> int:
        stmt = (
            select(func.count(func.distinct(RecommendationItem.question_id)))
            .join(RecommendationBatch, RecommendationBatch.id == RecommendationItem.batch_id)
            .join(
                ModelCoresetRun,
                ModelCoresetRun.recommendation_batch_id == RecommendationBatch.id,
            )
            .where(ModelCoresetRun.status == RUN_STATUS_SUCCESS)
            .where(ModelCoresetRun.data_scope == data_scope)
        )
        if up_to_created_at is not None:
            stmt = stmt.where(ModelCoresetRun.created_at <= up_to_created_at)
        return int(self.db.scalar(stmt) or 0)

    def _model_versions(self) -> list[ModelVersion]:
        return list(
            self.db.scalars(
                select(ModelVersion)
                .options(selectinload(ModelVersion.training_run))
                .where(ModelVersion.training_run_id.is_not(None))
                .where(ModelVersion.checkpoint_path.is_not(None))
                .order_by(ModelVersion.created_at.desc(), ModelVersion.id.desc())
                .limit(50)
            )
        )

    def _active_model_version_out(self) -> ModelVersionOut | None:
        version = self.db.scalar(
            select(ModelVersion)
            .options(selectinload(ModelVersion.training_run))
            .where(ModelVersion.is_active.is_(True))
            .where(ModelVersion.training_run_id.is_not(None))
            .where(ModelVersion.checkpoint_path.is_not(None))
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return self._model_version_out(version) if version else None

    def _completed_sample_count(self) -> int:
        return int(
            self.db.scalar(
                select(func.count(Question.id)).where(
                    Question.source_status == QUESTION_SOURCE_ACTIVE,
                    Question.annotation_status == QUESTION_STATUS_COMPLETED,
                )
            )
            or 0
        )

    def _pending_candidate_count(self) -> int:
        return int(
            self.db.scalar(
                select(func.count(Question.id)).where(
                    Question.source_status == QUESTION_SOURCE_ACTIVE,
                    Question.annotation_status == QUESTION_STATUS_PENDING,
                )
            )
            or 0
        )

    def _training_run_group_key(self, run: ModelTrainingRun) -> str:
        return _trend_group_key(
            params=run.params_json,
            target_stage=run.target_stage,
            model_type=_training_run_model_type(run),
            base_model_name=_training_run_base_model_name(run),
        )

    def _training_run_out(self, run: ModelTrainingRun) -> TrainingRunOut:
        linked_version = _linked_model_version(run)
        dataset_sample_count = run.train_sample_count + run.val_sample_count
        model_type = _training_run_model_type(run)
        base_model_name = _training_run_base_model_name(run)
        parameter_summary = _parameter_summary(
            params=run.params_json,
            target_stage=run.target_stage,
            model_type=model_type,
            base_model_name=base_model_name,
            sample_count=dataset_sample_count,
        )
        return TrainingRunOut(
            id=run.id,
            run_no=run.run_no,
            status=run.status,
            triggered_by_user_id=run.triggered_by_user_id,
            base_model_path=run.base_model_path,
            target_stage=run.target_stage,
            train_sample_count=run.train_sample_count,
            val_sample_count=run.val_sample_count,
            dataset_sample_count=dataset_sample_count,
            run_display_name=_training_run_display_name(run),
            model_type=model_type,
            base_model_name=base_model_name,
            parameter_summary=parameter_summary,
            trend_group_key=self._training_run_group_key(run),
            related_model_version_id=linked_version.id if linked_version else None,
            related_model_version_code=linked_version.version_code if linked_version else None,
            related_model_display_name=(
                _model_version_display_name(linked_version) if linked_version else None
            ),
            params_json=run.params_json,
            metrics_json=run.metrics_json,
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
            epochs=[
                TrainingEpochOut(
                    id=item.id,
                    training_run_id=item.training_run_id,
                    epoch_no=item.epoch_no,
                    train_loss=_decimal_to_float(item.train_loss),
                    val_loss=_decimal_to_float(item.val_loss),
                    level_accuracy=_decimal_to_float(item.level_accuracy),
                    macro_f1=_decimal_to_float(item.macro_f1),
                    detection_rate=_decimal_to_float(item.detection_rate),
                    created_at=item.created_at,
                )
                for item in sorted(run.epochs, key=lambda row: row.epoch_no)
            ],
        )

    def _model_version_out(self, version: ModelVersion) -> ModelVersionOut:
        run = version.training_run
        dataset_sample_count = version.train_sample_count + version.val_sample_count
        return ModelVersionOut(
            id=version.id,
            version_code=version.version_code,
            version_display_name=_model_version_display_name(version),
            model_type=version.model_type,
            base_model_name=version.base_model_name,
            artifact_path=version.artifact_path,
            training_run_id=version.training_run_id,
            source_run_no=run.run_no if run else None,
            source_run_display_name=_training_run_display_name(run) if run else None,
            checkpoint_path=version.checkpoint_path,
            is_active=version.is_active,
            level_accuracy=_decimal_to_float(version.level_accuracy),
            macro_f1=_decimal_to_float(version.macro_f1),
            detection_rate=_decimal_to_float(version.detection_rate),
            val_loss=_decimal_to_float(version.val_loss),
            train_sample_count=version.train_sample_count,
            val_sample_count=version.val_sample_count,
            dataset_sample_count=dataset_sample_count,
            parameter_summary=_parameter_summary(
                params=version.params_json,
                target_stage=run.target_stage if run else None,
                model_type=version.model_type,
                base_model_name=version.base_model_name,
                sample_count=dataset_sample_count,
            ),
            trend_group_key=_trend_group_key(
                params=version.params_json,
                target_stage=run.target_stage if run else None,
                model_type=version.model_type,
                base_model_name=version.base_model_name,
            ),
            params_json=version.params_json,
            created_at=version.created_at,
        )

    def _trend_groups_out(self, versions: list[ModelVersion]) -> list[TrendGroupOut]:
        grouped: dict[str, dict] = {}
        for version in versions:
            run = version.training_run
            key = _trend_group_key(
                params=version.params_json,
                target_stage=run.target_stage if run else None,
                model_type=version.model_type,
                base_model_name=version.base_model_name,
            )
            group = grouped.setdefault(
                key,
                {
                    "label": _trend_group_label(
                        params=version.params_json,
                        target_stage=run.target_stage if run else None,
                        model_type=version.model_type,
                        base_model_name=version.base_model_name,
                    ),
                    "parameter_summary": _parameter_summary(
                        params=version.params_json,
                        target_stage=run.target_stage if run else None,
                        model_type=version.model_type,
                        base_model_name=version.base_model_name,
                        sample_count=None,
                    ),
                    "target_stage": run.target_stage if run else "",
                    "model_type": version.model_type,
                    "base_model_name": version.base_model_name,
                    "points_by_dataset": {},
                },
            )
            dataset_key = (version.train_sample_count, version.val_sample_count)
            existing = group["points_by_dataset"].get(dataset_key)
            candidate = {
                "model_version_id": version.id,
                "training_run_id": version.training_run_id,
                "label": _model_version_display_name(version),
                "sample_label": _sample_label(version.train_sample_count, version.val_sample_count),
                "sample_count": version.train_sample_count + version.val_sample_count,
                "train_sample_count": version.train_sample_count,
                "val_sample_count": version.val_sample_count,
                "level_accuracy": _decimal_to_float(version.level_accuracy),
                "macro_f1": _decimal_to_float(version.macro_f1),
                "detection_rate": _decimal_to_float(version.detection_rate),
                "created_at": version.created_at,
            }
            if existing is None or existing["created_at"] <= version.created_at:
                group["points_by_dataset"][dataset_key] = candidate

        result: list[TrendGroupOut] = []
        for key, group in grouped.items():
            points = sorted(
                group["points_by_dataset"].values(),
                key=lambda item: (
                    item["sample_count"],
                    item["train_sample_count"],
                    item["val_sample_count"],
                    item["created_at"],
                ),
            )
            result.append(
                TrendGroupOut(
                    key=key,
                    label=group["label"],
                    parameter_summary=group["parameter_summary"],
                    target_stage=group["target_stage"],
                    model_type=group["model_type"],
                    base_model_name=group["base_model_name"],
                    point_count=len(points),
                    points=[
                        TrendPointOut(
                            model_version_id=item["model_version_id"],
                            training_run_id=item["training_run_id"],
                            label=item["label"],
                            sample_label=item["sample_label"],
                            sample_count=item["sample_count"],
                            train_sample_count=item["train_sample_count"],
                            val_sample_count=item["val_sample_count"],
                            level_accuracy=item["level_accuracy"],
                            macro_f1=item["macro_f1"],
                            detection_rate=item["detection_rate"],
                            created_at=item["created_at"],
                        )
                        for item in points
                    ],
                )
            )
        return sorted(result, key=lambda item: (item.label, item.key))

    def _prediction_run_out(
        self,
        run: ModelPredictionRun,
        *,
        include_items: bool = False,
    ) -> PredictionRunOut:
        items = getattr(run, "items", []) if include_items else []
        return PredictionRunOut(
            id=run.id,
            run_no=run.run_no,
            model_version_id=run.model_version_id,
            status=run.status,
            triggered_by_user_id=run.triggered_by_user_id,
            confidence_strategy=run.confidence_strategy,
            candidate_count=run.candidate_count,
            selected_count=run.selected_count,
            moved_count=run.moved_count,
            recommendation_batch_id=run.recommendation_batch_id,
            params_json=run.params_json,
            metrics_json=run.metrics_json,
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
            items=[
                PredictionItemOut(
                    id=item.id,
                    prediction_run_id=item.prediction_run_id,
                    question_id=item.question_id,
                    predicted_levels_json=item.predicted_levels_json,
                    confidence_score=float(item.confidence_score),
                    uncertainty_score=float(item.uncertainty_score),
                    rank_no=item.rank_no,
                    is_selected=item.is_selected,
                    created_at=item.created_at,
                )
                for item in sorted(items, key=lambda row: row.rank_no)
            ],
        )

    def _coreset_run_out(self, run: ModelCoresetRun) -> CoresetRunOut:
        batch = run.recommendation_batch
        batch_items = list(getattr(batch, "items", []) or [])
        question_ids = [
            item.question_id
            for item in sorted(batch_items, key=lambda row: (row.rank_no, row.id))
        ]
        moved_question_ids = [
            int(question_id)
            for question_id in (run.metrics_json or {}).get("moved_question_ids", []) or []
            if isinstance(question_id, int)
        ]
        update_mode = str((run.params_json or {}).get("update_mode") or "full")
        return CoresetRunOut(
            id=run.id,
            run_no=run.run_no,
            status=run.status,
            triggered_by_user_id=run.triggered_by_user_id,
            strategy=run.strategy,
            data_scope=run.data_scope,
            update_mode=update_mode if update_mode in {"full", "incremental"} else "full",
            requested_count=run.requested_count,
            candidate_count=run.candidate_count,
            selected_count=run.selected_count,
            moved_count=run.moved_count,
            recommendation_batch_id=run.recommendation_batch_id,
            batch_no=batch.batch_no if batch else run.run_no,
            recommendation_batch_no=batch.batch_no if batch else None,
            params_json=run.params_json,
            metrics_json=run.metrics_json,
            error_message=run.error_message,
            baseline_run_id=_summary_int(run.metrics_json or {}, "baseline_run_id"),
            baseline_run_no=(run.metrics_json or {}).get("baseline_run_no"),
            baseline_batch_no=(run.metrics_json or {}).get("baseline_batch_no"),
            started_at=run.started_at,
            finished_at=run.finished_at,
            created_at=run.created_at,
            question_ids=question_ids,
            moved_question_ids=moved_question_ids,
        )


def _linked_model_version(run: ModelTrainingRun | None) -> ModelVersion | None:
    if run is None:
        return None
    versions = list(getattr(run, "model_versions", []) or [])
    if not versions:
        return None
    return sorted(versions, key=lambda item: (item.created_at, item.id), reverse=True)[0]


def _training_run_model_type(run: ModelTrainingRun | None) -> str | None:
    return _linked_model_version(run).model_type if _linked_model_version(run) else None


def _training_run_base_model_name(run: ModelTrainingRun | None) -> str | None:
    return _linked_model_version(run).base_model_name if _linked_model_version(run) else None


def _training_run_display_name(run: ModelTrainingRun | None) -> str:
    if run is None:
        return "-"
    sample_count = run.train_sample_count + run.val_sample_count
    model_type = _training_run_model_type(run) or "model"
    stage = run.target_stage or "stage"
    timestamp = run.run_no.split("_")[1] if "_" in run.run_no else f"{run.created_at:%Y%m%d%H%M%S}"
    return f"{stage}-{model_type}-s{sample_count}-{timestamp}"


def _model_version_display_name(version: ModelVersion | None) -> str:
    if version is None:
        return "-"
    if re.fullmatch(r"M\d+", version.version_code or ""):
        stage = version.training_run.target_stage if version.training_run else "stage"
        sample_count = version.train_sample_count + version.val_sample_count
        timestamp = f"{version.created_at:%Y%m%d%H%M%S}"
        return f"{stage}-{version.model_type or 'model'}-s{sample_count}-{timestamp}"
    return version.version_code


def _sample_label(train_sample_count: int, val_sample_count: int) -> str:
    return f"{train_sample_count + val_sample_count} samples ({train_sample_count}/{val_sample_count})"


def _trend_group_key(
    *,
    params: dict | None,
    target_stage: str | None,
    model_type: str | None,
    base_model_name: str | None,
) -> str:
    payload = {
        "target_stage": target_stage or "",
        "model_type": model_type or "",
        "base_model_name": base_model_name or "",
        "epochs": params.get("epochs") if params else None,
        "batch_size": params.get("batch_size") if params else None,
        "learning_rate": params.get("learning_rate") if params else None,
        "val_size": params.get("val_size") if params else None,
        "patience": params.get("patience") if params else None,
        "max_length": params.get("max_length") if params else None,
        "include_gold_labels": bool(params.get("include_gold_labels")) if params else False,
        "random_seed": params.get("random_seed") if params else None,
        "device": params.get("device") if params else None,
    }
    return "|".join(f"{key}={payload[key]}" for key in sorted(payload))


def _trend_group_label(
    *,
    params: dict | None,
    target_stage: str | None,
    model_type: str | None,
    base_model_name: str | None,
) -> str:
    return _parameter_summary(
        params=params,
        target_stage=target_stage,
        model_type=model_type,
        base_model_name=base_model_name,
        sample_count=None,
    )


def _parameter_summary(
    *,
    params: dict | None,
    target_stage: str | None,
    model_type: str | None,
    base_model_name: str | None,
    sample_count: int | None,
) -> str:
    params = params or {}
    summary = [
        f"stage={target_stage or '-'}",
        f"model={model_type or '-'}",
        f"base={base_model_name or '-'}",
    ]
    if sample_count is not None:
        summary.append(f"samples={sample_count}")
    summary.extend(
        [
            f"epochs={params.get('epochs', '-')}",
            f"batch={params.get('batch_size', '-')}",
            f"lr={params.get('learning_rate', '-')}",
            f"val={params.get('val_size', '-')}",
            f"patience={params.get('patience', '-')}",
            f"max_len={params.get('max_length', '-')}",
            f"seed={params.get('random_seed', '-')}",
            f"gold={'yes' if params.get('include_gold_labels') else 'no'}",
            f"device={params.get('device', '-')}",
        ]
    )
    return ", ".join(summary)


def _sanitize_code_fragment(value: object, *, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip()).strip("-").lower()
    return text or fallback


def _learning_rate_fragment(value: object) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "na"
    return f"{numeric:.0e}".replace("+0", "").replace("+", "")


def _log_dir() -> Path:
    path = Path(__file__).resolve().parents[2] / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _training_run_log_path(run_id: int) -> Path:
    return _log_dir() / f"training_run_{run_id}.log"


def _active_learning_run_pid_path(job_type: str, run_id: int) -> Path:
    return _log_dir() / f"{job_type}_run_{run_id}.pid"


def _training_run_pid_path(run_id: int) -> Path:
    return _active_learning_run_pid_path("training", run_id)


def _prediction_run_pid_path(run_id: int) -> Path:
    return _active_learning_run_pid_path("prediction", run_id)


def _training_stderr_log_path() -> Path:
    return _log_dir() / "active_learning_training.err.log"


def _tail_text(path: Path, max_bytes: int) -> tuple[str, bool]:
    if not path.exists():
        return "", False
    size = path.stat().st_size
    is_truncated = size > max_bytes
    with path.open("rb") as file:
        if is_truncated:
            file.seek(-max_bytes, os.SEEK_END)
        data = file.read()
    return data.decode("utf-8", errors="replace"), is_truncated


class _RunLogger:
    def __init__(self, run_id: int) -> None:
        self.path = _training_run_log_path(run_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, message: str) -> None:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self.path.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp} UTC] {message}\n")


def _worker_pid_from_file(job_type: str, run_id: int) -> int | None:
    path = _active_learning_run_pid_path(job_type, run_id)
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _find_worker_pid_for_run(job_type: str, run_id: int) -> int | None:
    if os.name != "nt":
        return None
    try:
        result = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                "name='python.exe'",
                "get",
                "ProcessId,CommandLine",
                "/format:csv",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    needle = f"active_learning_worker {job_type} {run_id}"
    for line in result.stdout.splitlines():
        if needle not in line:
            continue
        parts = [part.strip() for part in line.split(",")]
        if not parts:
            continue
        try:
            return int(parts[-1])
        except ValueError:
            continue
    return None


def _terminate_process(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except OSError:
        return False


def _terminate_active_learning_worker(job_type: str, run_id: int) -> bool:
    pid = _worker_pid_from_file(job_type, run_id) or _find_worker_pid_for_run(job_type, run_id)
    if pid is None:
        return False
    terminated = _terminate_process(pid)
    if terminated:
        _active_learning_run_pid_path(job_type, run_id).unlink(missing_ok=True)
    return terminated


def _terminate_training_worker(run_id: int) -> bool:
    return _terminate_active_learning_worker("training", run_id)


def _terminate_prediction_worker(run_id: int) -> bool:
    return _terminate_active_learning_worker("prediction", run_id)


def _terminate_coreset_worker(run_id: int) -> bool:
    return _terminate_active_learning_worker("coreset", run_id)


def _run_training_job(run_id: int) -> None:
    db = SessionLocal()
    try:
        _ActiveLearningRunner(db).run_training(run_id)
    finally:
        db.close()


def _run_prediction_job(run_id: int) -> None:
    db = SessionLocal()
    try:
        _ActiveLearningRunner(db).run_prediction(run_id)
    finally:
        db.close()


def _run_coreset_job(run_id: int) -> None:
    db = SessionLocal()
    try:
        _ActiveLearningRunner(db).run_coreset(run_id)
    finally:
        db.close()


def _resolve_worker_python_for_device(device: str) -> str:
    settings = get_settings()
    default_python = settings.active_learning_worker_python or sys.executable
    if device == "cuda":
        return settings.active_learning_gpu_worker_python or default_python
    if device == "auto":
        return settings.active_learning_gpu_worker_python or default_python
    return default_python


@lru_cache(maxsize=8)
def _resolve_base_model_metadata(model_path: str) -> tuple[str, str]:
    from transformers import AutoConfig

    settings = get_settings()
    config = AutoConfig.from_pretrained(model_path)
    model_type = str(getattr(config, "model_type", "") or "unknown")
    resolved_path = os.path.abspath(model_path)
    base_model_name = Path(
        str(getattr(config, "_name_or_path", "") or model_path)
    ).name or Path(model_path).name
    configured_name = (settings.embedding_model_name or "").strip()
    configured_path = os.path.abspath(settings.embedding_model_path)
    configured_tokens = {
        token for token in re.split(r"[^a-z0-9]+", configured_name.lower()) if token
    }
    if (
        resolved_path == configured_path
        and configured_name
        and model_type.lower() in configured_tokens
    ):
        base_model_name = configured_name
    return model_type, base_model_name


def _spawn_active_learning_worker(
    job_type: str,
    run_id: int,
    *,
    python_executable: str | None = None,
) -> subprocess.Popen:
    settings = get_settings()
    python_executable = python_executable or settings.active_learning_worker_python or sys.executable
    backend_root = Path(__file__).resolve().parents[2]
    log_dir = backend_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    thread_count = str(max(1, settings.active_learning_torch_threads))
    env.setdefault("OMP_NUM_THREADS", thread_count)
    env.setdefault("MKL_NUM_THREADS", thread_count)
    env.setdefault("NUMEXPR_NUM_THREADS", thread_count)
    env.setdefault("OPENBLAS_NUM_THREADS", thread_count)
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    env.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

    stdout_path = log_dir / f"active_learning_{job_type}.out.log"
    stderr_path = log_dir / f"active_learning_{job_type}.err.log"
    stdout = stdout_path.open("a", encoding="utf-8")
    stderr = stderr_path.open("a", encoding="utf-8")
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            [
                python_executable,
                "-m",
                "app.tasks.active_learning_worker",
                job_type,
                str(run_id),
            ],
            cwd=backend_root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            close_fds=True,
            creationflags=creationflags,
        )
        _active_learning_run_pid_path(job_type, run_id).write_text(str(process.pid), encoding="utf-8")
        return process
    finally:
        stdout.close()
        stderr.close()


class _ActiveLearningRunner:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.selector = CoresetSelector()

    def run_training(self, run_id: int) -> None:
        logger = _RunLogger(run_id)
        run = self.db.get(ModelTrainingRun, run_id)
        if run is None:
            logger.write(f"Training run {run_id} was not found.")
            return
        try:
            logger.write(f"Training run {run.run_no} starting.")
            run.status = RUN_STATUS_RUNNING
            run.started_at = datetime.utcnow()
            self.db.commit()

            params = TrainingRunCreateRequest.model_validate(run.params_json or {})
            logger.write(
                "Params: "
                f"epochs={params.epochs}, batch_size={params.batch_size}, "
                f"learning_rate={params.learning_rate}, val_size={params.val_size}, "
                f"max_length={params.max_length}, random_seed={params.random_seed}, "
                f"include_gold_labels={params.include_gold_labels}, device={params.device}."
            )
            competency_ids = self._target_competency_ids(params.target_stage)
            logger.write(
                f"Target stage={params.target_stage}, competency_count={len(competency_ids)}."
            )
            examples = self._training_examples(params, competency_ids)
            logger.write(f"Loaded trainable examples: {len(examples)}.")
            if len(examples) < params.min_train_samples:
                raise RuntimeError(
                    f"Not enough trainable examples: current={len(examples)}, "
                    f"required={params.min_train_samples}."
                )

            train_examples, val_examples = self._split_examples(
                examples,
                params.val_size,
                params.random_seed,
            )
            logger.write(
                f"Split examples: train={len(train_examples)}, validation={len(val_examples)}."
            )
            run.train_sample_count = len(train_examples)
            run.val_sample_count = len(val_examples)
            self.db.commit()

            logger.write(f"Loading base model from {run.base_model_path}.")
            model = _TorchCompetencyModel(
                model_path=run.base_model_path,
                num_competencies=len(competency_ids),
                num_levels=NUM_LEVELS,
                batch_size=params.batch_size,
                max_length=params.max_length,
                device=params.device,
                random_seed=params.random_seed,
            )
            logger.write(f"Model loaded on device={model.device}. Starting fit.")
            best_metrics = model.fit(
                train_examples,
                val_examples,
                epochs=params.epochs,
                learning_rate=params.learning_rate,
                patience=params.patience,
                random_seed=params.random_seed,
                epoch_callback=lambda epoch_no, metrics: self._record_epoch(
                    run_id,
                    epoch_no,
                    metrics,
                ),
                progress_callback=logger.write,
            )
            checkpoint_path = self._checkpoint_path(run.run_no)
            logger.write(f"Best metrics: {best_metrics}.")
            logger.write(f"Saving checkpoint to {checkpoint_path}.")
            model.save_checkpoint(
                checkpoint_path,
                metadata={
                    "run_id": run.id,
                    "run_no": run.run_no,
                    "target_stage": params.target_stage,
                    "competency_ids": competency_ids,
                    "params": params.model_dump(),
                    "metrics": best_metrics,
                },
            )
            model_type, base_model_name = _resolve_base_model_metadata(run.base_model_path)
            logger.write(
                f"Resolved base model metadata: model_type={model_type}, "
                f"base_model_name={base_model_name}."
            )

            for version in self.db.scalars(
                select(ModelVersion).where(ModelVersion.is_active.is_(True))
            ):
                version.is_active = False
            version = ModelVersion(
                version_code=self._next_version_code(
                    run=run,
                    params=params.model_dump(),
                    model_type=model_type,
                    sample_count=len(examples),
                ),
                model_type=model_type,
                base_model_name=base_model_name,
                artifact_path=checkpoint_path,
                metrics_json=best_metrics,
                training_run_id=run.id,
                checkpoint_path=checkpoint_path,
                is_active=True,
                level_accuracy=_metric_decimal(best_metrics.get("level_accuracy")),
                macro_f1=_metric_decimal(best_metrics.get("macro_f1")),
                detection_rate=_metric_decimal(best_metrics.get("detection_rate")),
                val_loss=_metric_decimal(best_metrics.get("val_loss")),
                train_sample_count=len(train_examples),
                val_sample_count=len(val_examples),
                params_json={
                    **params.model_dump(),
                    "competency_ids": competency_ids,
                },
                created_at=datetime.utcnow(),
            )
            self.db.add(version)

            run.status = RUN_STATUS_SUCCESS
            run.metrics_json = best_metrics
            run.finished_at = datetime.utcnow()
            self.db.commit()
            logger.write(f"Training run {run.run_no} finished successfully.")
            _training_run_pid_path(run_id).unlink(missing_ok=True)
        except Exception as exc:  # pragma: no cover - background failure path
            self.db.rollback()
            failed_run = self.db.get(ModelTrainingRun, run_id)
            if failed_run is not None:
                failed_run.status = RUN_STATUS_FAILED
                failed_run.error_message = str(exc)
                failed_run.finished_at = datetime.utcnow()
                self.db.commit()
            logger.write(f"Training run failed: {exc}")
            _training_run_pid_path(run_id).unlink(missing_ok=True)

    def run_prediction(self, run_id: int) -> None:
        run = self.db.scalar(
            select(ModelPredictionRun)
            .options(selectinload(ModelPredictionRun.model_version))
            .where(ModelPredictionRun.id == run_id)
            .with_for_update()
        )
        if run is None:
            return
        try:
            if run.status == RUN_STATUS_RUNNING and run.started_at is not None:
                return
            if run.status != RUN_STATUS_PENDING:
                return
            run.status = RUN_STATUS_RUNNING
            run.started_at = datetime.utcnow()
            run.candidate_count = 0
            run.selected_count = 0
            run.moved_count = 0
            run.metrics_json = {
                "processed_count": 0,
                "total_count": 0,
                "batch_size": 0,
            }
            self.db.commit()

            params = PredictionRunCreateRequest.model_validate(run.params_json or {})
            model_version = run.model_version
            model = _TorchCompetencyModel.load_from_checkpoint(
                model_version.checkpoint_path,
                batch_size=params.batch_size,
            )
            candidates = self._prediction_candidates(params)
            total_count = len(candidates)
            run.candidate_count = total_count
            run.metrics_json = {
                "processed_count": 0,
                "total_count": total_count,
                "batch_size": params.batch_size,
            }
            self.db.commit()

            def progress_callback(processed_count: int, total_count_value: int) -> None:
                run.metrics_json = {
                    "processed_count": processed_count,
                    "total_count": total_count_value,
                    "batch_size": params.batch_size,
                }
                self.db.commit()

            probabilities = model.predict_proba(
                [item.text for item in candidates],
                progress_callback=progress_callback,
            )
            scored_items = []
            for index, candidate in enumerate(candidates):
                probs = probabilities[index]
                predicted_levels = np.argmax(probs, axis=-1).astype(int).tolist()
                confidence, uncertainty = _confidence_scores(probs, params.confidence_strategy)
                scored_items.append(
                    {
                        "question_id": candidate.question_id,
                        "predicted_levels": predicted_levels,
                        "probabilities": np.round(probs, 6).tolist(),
                        "confidence": confidence,
                        "uncertainty": uncertainty,
                    }
                )
            scored_items.sort(key=lambda item: item["uncertainty"], reverse=True)
            selected = scored_items[: min(params.select_count, len(scored_items))]
            selected_ids = {int(item["question_id"]) for item in selected}

            recommendation_batch_id = None
            moved_count = 0
            if params.auto_move_to_waiting and selected:
                batch = RecommendationBatch(
                    batch_no=f"al_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
                    algorithm_code="active_learning_uncertainty",
                    triggered_by_user_id=run.triggered_by_user_id,
                    target_stage="annotation_pool",
                    context_json={
                        "prediction_run_id": run.id,
                        "model_version_id": model_version.id,
                        "confidence_strategy": params.confidence_strategy,
                        "requested_count": params.select_count,
                    },
                    created_at=datetime.utcnow(),
                )
                self.db.add(batch)
                self.db.flush()
                recommendation_batch_id = batch.id
                for rank_no, item in enumerate(selected, start=1):
                    self.db.add(
                        RecommendationItem(
                            batch_id=batch.id,
                            question_id=int(item["question_id"]),
                            score=Decimal(f"{item['uncertainty']:.6f}"),
                            rank_no=rank_no,
                            is_accepted=True,
                        )
                    )
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

            for rank_no, item in enumerate(scored_items, start=1):
                self.db.add(
                    ModelPredictionItem(
                        prediction_run_id=run.id,
                        question_id=int(item["question_id"]),
                        predicted_levels_json=item["predicted_levels"],
                        probabilities_json=item["probabilities"],
                        confidence_score=Decimal(f"{item['confidence']:.6f}"),
                        uncertainty_score=Decimal(f"{item['uncertainty']:.6f}"),
                        rank_no=rank_no,
                        is_selected=int(item["question_id"]) in selected_ids,
                        created_at=datetime.utcnow(),
                    )
                )

            run.status = RUN_STATUS_SUCCESS
            run.candidate_count = len(candidates)
            run.selected_count = len(selected)
            run.moved_count = moved_count
            run.recommendation_batch_id = recommendation_batch_id
            run.metrics_json = {
                "avg_confidence": _safe_mean(item["confidence"] for item in scored_items),
                "avg_uncertainty": _safe_mean(item["uncertainty"] for item in scored_items),
                "min_confidence": min((item["confidence"] for item in scored_items), default=None),
                "max_uncertainty": max(
                    (item["uncertainty"] for item in scored_items),
                    default=None,
                ),
                "processed_count": total_count,
                "total_count": total_count,
                "batch_size": params.batch_size,
            }
            run.finished_at = datetime.utcnow()
            self.db.commit()
        except Exception as exc:  # pragma: no cover - background failure path
            self.db.rollback()
            failed_run = self.db.get(ModelPredictionRun, run_id)
            if failed_run is not None:
                failed_run.status = RUN_STATUS_FAILED
                failed_run.error_message = str(exc)
                failed_run.finished_at = datetime.utcnow()
                self.db.commit()
        finally:
            _prediction_run_pid_path(run_id).unlink(missing_ok=True)

    def run_coreset(self, run_id: int) -> None:
        run = self.db.scalar(
            select(ModelCoresetRun)
            .options(selectinload(ModelCoresetRun.recommendation_batch))
            .where(ModelCoresetRun.id == run_id)
            .with_for_update()
        )
        if run is None:
            return
        try:
            if run.status == RUN_STATUS_RUNNING and run.started_at is not None:
                return
            if run.status != RUN_STATUS_PENDING:
                return

            run.status = RUN_STATUS_RUNNING
            run.started_at = datetime.utcnow()
            run.metrics_json = self._coreset_metrics(
                phase="preparing",
                progress_percent=5,
                progress_label="准备候选题",
                selection_mode=_default_coreset_selection_mode(run.strategy),
                update_mode=str((run.params_json or {}).get("update_mode") or "full"),
                baseline_run_id=_summary_int(run.metrics_json or {}, "baseline_run_id"),
                baseline_run_no=(run.metrics_json or {}).get("baseline_run_no"),
                baseline_batch_no=(run.metrics_json or {}).get("baseline_batch_no"),
                snapshot_created_before=(run.metrics_json or {}).get("snapshot_created_before"),
            )
            self.db.commit()

            params = CoresetRunCreateRequest.model_validate(run.params_json or {})
            update_mode = params.update_mode
            baseline_run = self._load_incremental_baseline_for_run(run, params.data_scope)
            if update_mode == "incremental" and baseline_run is None:
                raise RuntimeError(
                    "Incremental CoreSet baseline is missing. Please rerun a full-pool CoreSet."
                )
            baseline_cutoff = _snapshot_cutoff_from_run(baseline_run)
            embedding_model = EmbeddingService(self.db).get_or_create_model()
            candidates = self._coreset_candidates(
                data_scope=params.data_scope,
                embedding_model_id=embedding_model.id,
                created_after=baseline_cutoff if update_mode == "incremental" else None,
            )
            anchor_candidates = (
                self._incremental_anchor_candidates(
                    data_scope=params.data_scope,
                    embedding_model_id=embedding_model.id,
                    up_to_created_at=baseline_run.created_at if baseline_run else None,
                )
                if update_mode == "incremental"
                else []
            )
            anchor_count = len(anchor_candidates)
            snapshot_created_before = _candidate_snapshot_cutoff(candidates, baseline_cutoff)
            run.candidate_count = len(candidates)
            run.metrics_json = self._coreset_metrics(
                phase="loading_candidates",
                progress_percent=20,
                progress_label="已加载候选向量",
                candidate_count=len(candidates),
                embedding_model_code=embedding_model.model_code,
                embedding_model_name=embedding_model.model_name,
                selection_mode=_default_coreset_selection_mode(run.strategy),
                update_mode=update_mode,
                baseline_run_id=baseline_run.id if baseline_run else None,
                baseline_run_no=baseline_run.run_no if baseline_run else None,
                baseline_batch_no=baseline_run.recommendation_batch.batch_no
                if baseline_run and baseline_run.recommendation_batch
                else None,
                snapshot_created_before=snapshot_created_before.isoformat()
                if snapshot_created_before
                else None,
                anchor_count=anchor_count if update_mode == "incremental" else None,
            )
            self.db.commit()

            if not candidates:
                run.status = RUN_STATUS_SUCCESS
                run.selected_count = 0
                run.moved_count = 0
                run.finished_at = datetime.utcnow()
                run.metrics_json = self._coreset_metrics(
                    phase="finished",
                    progress_percent=100,
                    progress_label="候选池为空",
                    candidate_count=0,
                    selected_count=0,
                    moved_count=0,
                    embedding_model_code=embedding_model.model_code,
                    selection_mode=_default_coreset_selection_mode(run.strategy),
                    update_mode=update_mode,
                    baseline_run_id=baseline_run.id if baseline_run else None,
                    baseline_run_no=baseline_run.run_no if baseline_run else None,
                    baseline_batch_no=baseline_run.recommendation_batch.batch_no
                    if baseline_run and baseline_run.recommendation_batch
                    else None,
                    snapshot_created_before=snapshot_created_before.isoformat()
                    if snapshot_created_before
                    else None,
                    anchor_count=anchor_count if update_mode == "incremental" else None,
                )
                self.db.commit()
                return

            def update_progress(
                *,
                phase: str,
                progress_percent: int,
                progress_label: str,
                processed_count: int | None = None,
                total_count: int | None = None,
                selection_mode: str | None = None,
            ) -> None:
                run.metrics_json = self._coreset_metrics(
                    phase=phase,
                    progress_percent=progress_percent,
                    progress_label=progress_label,
                    candidate_count=len(candidates),
                    processed_count=processed_count,
                    total_count=total_count,
                    embedding_model_code=embedding_model.model_code,
                    embedding_model_name=embedding_model.model_name,
                    selection_mode=selection_mode
                    or _default_coreset_selection_mode(run.strategy),
                    update_mode=update_mode,
                    baseline_run_id=baseline_run.id if baseline_run else None,
                    baseline_run_no=baseline_run.run_no if baseline_run else None,
                    baseline_batch_no=baseline_run.recommendation_batch.batch_no
                    if baseline_run and baseline_run.recommendation_batch
                    else None,
                    snapshot_created_before=snapshot_created_before.isoformat()
                    if snapshot_created_before
                    else None,
                    anchor_count=anchor_count if update_mode == "incremental" else None,
                )
                self.db.commit()

            phase_label = _coreset_phase_label(run.strategy, update_mode)
            selection_mode_hint = _default_coreset_selection_mode(run.strategy)
            update_progress(
                phase="selecting",
                progress_percent=35,
                progress_label=phase_label,
                total_count=len(candidates),
                selection_mode=selection_mode_hint,
            )
            if update_mode == "incremental":
                selections = self.selector.select_incremental(
                    candidates,
                    anchor_candidates,
                    run.strategy,
                    run.requested_count,
                    progress_callback=lambda processed_count, total_count: update_progress(
                        phase="selecting",
                        progress_percent=min(
                            92,
                            35 + round((processed_count / max(total_count, 1)) * 45),
                        ),
                        progress_label=phase_label,
                        processed_count=processed_count,
                        total_count=total_count,
                        selection_mode=selection_mode_hint,
                    ),
                )
            else:
                selections = self.selector.select_full_pool(
                    candidates,
                    run.strategy,
                    run.requested_count,
                    progress_callback=lambda processed_count, total_count: update_progress(
                        phase="selecting",
                        progress_percent=min(
                            92,
                            35 + round((processed_count / max(total_count, 1)) * 45),
                        ),
                        progress_label=phase_label,
                        processed_count=processed_count,
                        total_count=total_count,
                        selection_mode=selection_mode_hint,
                    ),
                )
            selection_summary = dict(self.selector.last_summary)
            selection_mode = str(
                selection_summary.get("selection_mode") or selection_mode_hint
            )

            selected_ids = [item.question_id for item in selections]
            run.selected_count = len(selections)
            update_progress(
                phase="writing_batch",
                progress_percent=94,
                progress_label="写入批次与题池",
                processed_count=len(selections),
                total_count=len(candidates),
                selection_mode=selection_mode,
            )

            batch = RecommendationBatch(
                batch_no=f"rec_{datetime.utcnow():%Y%m%d%H%M%S}_{uuid4().hex[:8]}",
                algorithm_code=run.strategy,
                triggered_by_user_id=run.triggered_by_user_id,
                target_stage="annotation_pool",
                context_json={
                    "requested_count": run.requested_count,
                    "candidate_count": len(candidates),
                    "data_scope": run.data_scope,
                    "update_mode": update_mode,
                    "status_from": QUESTION_STATUS_PENDING if run.data_scope == "pending" else "ALL",
                    "status_to": QUESTION_STATUS_WAITING,
                    "selection_mode": selection_mode,
                    "embedding_model_code": embedding_model.model_code,
                    "baseline_run_id": baseline_run.id if baseline_run else None,
                    "baseline_run_no": baseline_run.run_no if baseline_run else None,
                    "baseline_batch_no": baseline_run.recommendation_batch.batch_no
                    if baseline_run and baseline_run.recommendation_batch
                    else None,
                    "anchor_count": anchor_count,
                    "snapshot_created_before": snapshot_created_before.isoformat()
                    if snapshot_created_before
                    else None,
                    "selection_summary": selection_summary,
                },
                created_at=datetime.utcnow(),
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
                    algorithm_code=run.strategy,
                    params_json={
                        "count": run.requested_count,
                        "data_scope": run.data_scope,
                        "update_mode": update_mode,
                        "baseline_run_id": baseline_run.id if baseline_run else None,
                    },
                    metrics_json={
                        "candidate_count": len(candidates),
                        "working_candidate_count": len(candidates),
                        "selected_count": len(selections),
                        "moved_count": moved_count,
                        "selection_mode": selection_mode,
                        "embedding_model_code": embedding_model.model_code,
                        "update_mode": update_mode,
                        "anchor_count": anchor_count,
                        "snapshot_created_before": snapshot_created_before.isoformat()
                        if snapshot_created_before
                        else None,
                        "selection_summary": selection_summary,
                    },
                    selected_question_count=len(selections),
                    created_at=datetime.utcnow(),
                )
            )

            run.status = RUN_STATUS_SUCCESS
            run.moved_count = moved_count
            run.recommendation_batch_id = batch.id
            run.finished_at = datetime.utcnow()
            run.metrics_json = self._coreset_metrics(
                phase="finished",
                progress_percent=100,
                progress_label="选题完成",
                candidate_count=len(candidates),
                processed_count=len(candidates),
                total_count=len(candidates),
                selected_count=len(selections),
                moved_count=moved_count,
                embedding_model_code=embedding_model.model_code,
                embedding_model_name=embedding_model.model_name,
                selection_mode=selection_mode,
                update_mode=update_mode,
                moved_question_ids=moved_question_ids,
                baseline_run_id=baseline_run.id if baseline_run else None,
                baseline_run_no=baseline_run.run_no if baseline_run else None,
                baseline_batch_no=baseline_run.recommendation_batch.batch_no
                if baseline_run and baseline_run.recommendation_batch
                else None,
                snapshot_created_before=snapshot_created_before.isoformat()
                if snapshot_created_before
                else None,
                anchor_count=anchor_count if update_mode == "incremental" else None,
                cluster_count=_summary_int(selection_summary, "cluster_count"),
                nonempty_cluster_count=_summary_int(
                    selection_summary, "nonempty_cluster_count"
                ),
                largest_cluster_size=_summary_int(
                    selection_summary, "largest_cluster_size"
                ),
                smallest_cluster_size=_summary_int(
                    selection_summary, "smallest_cluster_size"
                ),
            )
            self.db.commit()
        except Exception as exc:  # pragma: no cover - background failure path
            self.db.rollback()
            failed_run = self.db.get(ModelCoresetRun, run_id)
            if failed_run is not None:
                failed_run.status = RUN_STATUS_FAILED
                failed_run.error_message = str(exc)
                failed_run.finished_at = datetime.utcnow()
                failed_run.metrics_json = self._coreset_metrics(
                    phase="failed",
                    progress_percent=0,
                    progress_label="任务失败",
                    candidate_count=failed_run.candidate_count,
                    selected_count=failed_run.selected_count,
                    moved_count=failed_run.moved_count,
                    selection_mode=_default_coreset_selection_mode(
                        failed_run.strategy
                    ),
                    update_mode=str((failed_run.params_json or {}).get("update_mode") or "full"),
                    baseline_run_id=_summary_int(failed_run.metrics_json or {}, "baseline_run_id"),
                    baseline_run_no=(failed_run.metrics_json or {}).get("baseline_run_no"),
                    baseline_batch_no=(failed_run.metrics_json or {}).get("baseline_batch_no"),
                    snapshot_created_before=(failed_run.metrics_json or {}).get(
                        "snapshot_created_before"
                    ),
                    anchor_count=_summary_int(failed_run.metrics_json or {}, "anchor_count"),
                    error_message=str(exc),
                )
                self.db.commit()
        finally:
            _active_learning_run_pid_path("coreset", run_id).unlink(missing_ok=True)

    def _coreset_candidates(
        self,
        *,
        data_scope: str,
        embedding_model_id: int,
        created_after: datetime | None = None,
    ) -> list[CoresetCandidate]:
        stmt = (
            select(
                Question.id,
                QuestionContent.stem_text,
                QuestionEmbedding.vector_json,
                Question.created_at,
            )
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .outerjoin(
                QuestionEmbedding,
                and_(
                    QuestionEmbedding.question_id == Question.id,
                    QuestionEmbedding.embedding_model_id == embedding_model_id,
                ),
            )
            .where(Question.source_status == QUESTION_SOURCE_ACTIVE)
            .where(QuestionContent.stem_text != "")
            .order_by(Question.id.asc(), QuestionEmbedding.computed_at.desc())
        )
        if data_scope == "pending":
            stmt = stmt.where(Question.annotation_status == QUESTION_STATUS_PENDING)
        if created_after is not None:
            stmt = stmt.where(Question.created_at > created_after)

        candidates: list[CoresetCandidate] = []
        seen_ids: set[int] = set()
        for question_id, stem_text, vector_json, created_at in self.db.execute(stmt):
            if question_id in seen_ids:
                continue
            seen_ids.add(int(question_id))
            candidates.append(
                CoresetCandidate(
                    question_id=int(question_id),
                    text=str(stem_text or ""),
                    embedding=[float(value) for value in vector_json] if vector_json else None,
                    created_at=created_at,
                )
            )
        return candidates

    def _incremental_anchor_candidates(
        self,
        *,
        data_scope: str,
        embedding_model_id: int,
        up_to_created_at: datetime | None,
    ) -> list[CoresetCandidate]:
        stmt = (
            select(
                Question.id,
                QuestionContent.stem_text,
                QuestionEmbedding.vector_json,
                Question.created_at,
            )
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .join(RecommendationItem, RecommendationItem.question_id == Question.id)
            .join(RecommendationBatch, RecommendationBatch.id == RecommendationItem.batch_id)
            .join(
                ModelCoresetRun,
                ModelCoresetRun.recommendation_batch_id == RecommendationBatch.id,
            )
            .outerjoin(
                QuestionEmbedding,
                and_(
                    QuestionEmbedding.question_id == Question.id,
                    QuestionEmbedding.embedding_model_id == embedding_model_id,
                ),
            )
            .where(ModelCoresetRun.status == RUN_STATUS_SUCCESS)
            .where(ModelCoresetRun.data_scope == data_scope)
            .order_by(Question.id.asc(), ModelCoresetRun.created_at.asc())
        )
        if up_to_created_at is not None:
            stmt = stmt.where(ModelCoresetRun.created_at <= up_to_created_at)

        candidates: list[CoresetCandidate] = []
        seen_ids: set[int] = set()
        for question_id, stem_text, vector_json, created_at in self.db.execute(stmt):
            if question_id in seen_ids:
                continue
            seen_ids.add(int(question_id))
            candidates.append(
                CoresetCandidate(
                    question_id=int(question_id),
                    text=str(stem_text or ""),
                    embedding=[float(value) for value in vector_json] if vector_json else None,
                    created_at=created_at,
                )
            )
        return candidates

    def _count_incremental_candidates(
        self,
        *,
        data_scope: str,
        created_after: datetime | None,
    ) -> int:
        stmt = (
            select(func.count(Question.id))
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .where(Question.source_status == QUESTION_SOURCE_ACTIVE)
            .where(QuestionContent.stem_text != "")
        )
        if data_scope == "pending":
            stmt = stmt.where(Question.annotation_status == QUESTION_STATUS_PENDING)
        if created_after is not None:
            stmt = stmt.where(Question.created_at > created_after)
        return int(self.db.scalar(stmt) or 0)

    def _count_incremental_anchor_questions(
        self,
        *,
        data_scope: str,
        up_to_created_at: datetime | None,
    ) -> int:
        stmt = (
            select(func.count(func.distinct(RecommendationItem.question_id)))
            .join(RecommendationBatch, RecommendationBatch.id == RecommendationItem.batch_id)
            .join(
                ModelCoresetRun,
                ModelCoresetRun.recommendation_batch_id == RecommendationBatch.id,
            )
            .where(ModelCoresetRun.status == RUN_STATUS_SUCCESS)
            .where(ModelCoresetRun.data_scope == data_scope)
        )
        if up_to_created_at is not None:
            stmt = stmt.where(ModelCoresetRun.created_at <= up_to_created_at)
        return int(self.db.scalar(stmt) or 0)

    def _load_incremental_baseline_for_run(
        self,
        run: ModelCoresetRun,
        data_scope: str,
    ) -> ModelCoresetRun | None:
        baseline_run_id = _summary_int(run.metrics_json or {}, "baseline_run_id")
        if baseline_run_id is not None:
            return self.db.scalar(
                select(ModelCoresetRun)
                .options(selectinload(ModelCoresetRun.recommendation_batch))
                .where(ModelCoresetRun.id == baseline_run_id)
            )
        if (run.params_json or {}).get("update_mode") == "incremental":
            return self._resolve_incremental_baseline(data_scope)
        return None

    def _coreset_metrics(
        self,
        *,
        phase: str,
        progress_percent: int,
        progress_label: str,
        selection_mode: str,
        update_mode: str = "full",
        candidate_count: int | None = None,
        processed_count: int | None = None,
        total_count: int | None = None,
        selected_count: int | None = None,
        moved_count: int | None = None,
        embedding_model_code: str | None = None,
        embedding_model_name: str | None = None,
        moved_question_ids: list[int] | None = None,
        error_message: str | None = None,
        baseline_run_id: int | None = None,
        baseline_run_no: str | None = None,
        baseline_batch_no: str | None = None,
        snapshot_created_before: str | None = None,
        anchor_count: int | None = None,
        cluster_count: int | None = None,
        nonempty_cluster_count: int | None = None,
        largest_cluster_size: int | None = None,
        smallest_cluster_size: int | None = None,
    ) -> dict:
        metrics: dict[str, object] = {
            "phase": phase,
            "progress_percent": progress_percent,
            "progress_label": progress_label,
            "selection_mode": selection_mode,
            "update_mode": update_mode,
        }
        if candidate_count is not None:
            metrics["candidate_count"] = candidate_count
        if processed_count is not None:
            metrics["processed_count"] = processed_count
        if total_count is not None:
            metrics["total_count"] = total_count
        if selected_count is not None:
            metrics["selected_count"] = selected_count
        if moved_count is not None:
            metrics["moved_count"] = moved_count
        if embedding_model_code:
            metrics["embedding_model_code"] = embedding_model_code
        if embedding_model_name:
            metrics["embedding_model_name"] = embedding_model_name
        if moved_question_ids is not None:
            metrics["moved_question_ids"] = moved_question_ids
        if error_message:
            metrics["error_message"] = error_message
        if baseline_run_id is not None:
            metrics["baseline_run_id"] = baseline_run_id
        if baseline_run_no:
            metrics["baseline_run_no"] = baseline_run_no
        if baseline_batch_no:
            metrics["baseline_batch_no"] = baseline_batch_no
        if snapshot_created_before:
            metrics["snapshot_created_before"] = snapshot_created_before
        if anchor_count is not None:
            metrics["anchor_count"] = anchor_count
        if cluster_count is not None:
            metrics["cluster_count"] = cluster_count
        if nonempty_cluster_count is not None:
            metrics["nonempty_cluster_count"] = nonempty_cluster_count
        if largest_cluster_size is not None:
            metrics["largest_cluster_size"] = largest_cluster_size
        if smallest_cluster_size is not None:
            metrics["smallest_cluster_size"] = smallest_cluster_size
        return metrics

    def _target_competency_ids(self, target_stage: str) -> list[int]:
        stage_codes = STAGE_COMPETENCY_CODES.get(target_stage, [])
        if stage_codes:
            rows = self.db.execute(
                select(Competency.id, Competency.code)
                .where(Competency.code.in_(stage_codes))
                .order_by(Competency.display_order.asc())
            ).all()
            code_order = {code: idx for idx, code in enumerate(stage_codes)}
            ordered = sorted(rows, key=lambda row: code_order.get(str(row.code), 999))
            if len(ordered) == len(stage_codes):
                return [int(row.id) for row in ordered]
        return [
            int(row[0])
            for row in self.db.execute(
                select(Competency.id).order_by(Competency.display_order.asc()).limit(9)
            ).all()
        ]

    def _training_examples(
        self,
        params: TrainingRunCreateRequest,
        competency_ids: list[int],
    ) -> list[TrainingExample]:
        label_index = {competency_id: index for index, competency_id in enumerate(competency_ids)}
        examples: dict[int, TrainingExample] = {}

        stmt = (
            select(Question, QuestionLabelAggregate)
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .join(QuestionLabelAggregate, QuestionLabelAggregate.question_id == Question.id)
            .join(Grade, Grade.id == Question.grade_id)
            .options(
                selectinload(Question.content),
                selectinload(QuestionLabelAggregate.competencies),
            )
            .where(Question.source_status == QUESTION_SOURCE_ACTIVE)
            .where(Question.annotation_status == QUESTION_STATUS_COMPLETED)
            .where(Grade.edu_stage == params.target_stage)
            .where(QuestionContent.stem_text != "")
            .order_by(Question.id.asc())
        )
        for question, aggregate in self.db.execute(stmt).unique():
            labels = _labels_from_competencies(aggregate.competencies, label_index)
            examples[question.id] = TrainingExample(
                question_id=question.id,
                text=_question_text(question),
                labels=labels,
            )

        if params.include_gold_labels:
            gold_stmt = (
                select(QuestionGoldLabel)
                .join(Question, Question.id == QuestionGoldLabel.question_id)
                .join(QuestionContent, QuestionContent.question_id == Question.id)
                .join(Grade, Grade.id == Question.grade_id)
                .options(
                    selectinload(QuestionGoldLabel.question).selectinload(Question.content),
                    selectinload(QuestionGoldLabel.competencies),
                )
                .where(Grade.edu_stage == params.target_stage)
                .where(QuestionContent.stem_text != "")
                .order_by(QuestionGoldLabel.question_id.asc(), QuestionGoldLabel.id.asc())
            )
            for gold_label in self.db.scalars(gold_stmt).unique():
                if gold_label.question_id in examples:
                    continue
                examples[gold_label.question_id] = TrainingExample(
                    question_id=gold_label.question_id,
                    text=_question_text(gold_label.question),
                    labels=_labels_from_competencies(gold_label.competencies, label_index),
                )

        return list(examples.values())

    def _prediction_candidates(
        self,
        params: PredictionRunCreateRequest,
    ) -> list[PredictionCandidate]:
        stmt = (
            select(Question)
            .join(QuestionContent, QuestionContent.question_id == Question.id)
            .join(Grade, Grade.id == Question.grade_id)
            .options(selectinload(Question.content))
            .where(Question.source_status == QUESTION_SOURCE_ACTIVE)
            .where(Question.annotation_status == QUESTION_STATUS_PENDING)
            .where(Grade.edu_stage == params.target_stage)
            .where(QuestionContent.stem_text != "")
            .order_by(Question.id.asc())
        )
        return [
            PredictionCandidate(question_id=question.id, text=_question_text(question))
            for question in self.db.scalars(stmt).unique()
        ]

    def _split_examples(
        self,
        examples: list[TrainingExample],
        val_size: float,
        random_seed: int,
    ) -> tuple[list[TrainingExample], list[TrainingExample]]:
        shuffled = list(examples)
        random.Random(random_seed).shuffle(shuffled)
        val_count = max(1, int(round(len(shuffled) * val_size))) if len(shuffled) > 1 else 0
        val_examples = shuffled[:val_count]
        train_examples = shuffled[val_count:]
        if not train_examples and val_examples:
            train_examples.append(val_examples.pop())
        return train_examples, val_examples

    def _record_epoch(self, run_id: int, epoch_no: int, metrics: dict[str, float]) -> None:
        self.db.add(
            ModelTrainingEpoch(
                training_run_id=run_id,
                epoch_no=epoch_no,
                train_loss=_metric_decimal(metrics.get("train_loss")),
                val_loss=_metric_decimal(metrics.get("val_loss")),
                level_accuracy=_metric_decimal(metrics.get("level_accuracy")),
                macro_f1=_metric_decimal(metrics.get("macro_f1")),
                detection_rate=_metric_decimal(metrics.get("detection_rate")),
                created_at=datetime.utcnow(),
            )
        )
        self.db.commit()

    def _checkpoint_path(self, run_no: str) -> str:
        root = self.settings.active_learning_checkpoint_dir
        if not os.path.isabs(root):
            root = os.path.abspath(root)
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, f"{run_no}.pth")

    def _next_version_code(
        self,
        *,
        run: ModelTrainingRun,
        params: dict,
        model_type: str,
        sample_count: int,
    ) -> str:
        timestamp = run.run_no.split("_")[1] if "_" in run.run_no else f"{datetime.utcnow():%Y%m%d%H%M%S}"
        unique_suffix = run.run_no.split("_")[-1][:4]
        parts = [
            _sanitize_code_fragment(run.target_stage, fallback="stage"),
            _sanitize_code_fragment(model_type, fallback="model"),
            f"s{sample_count}",
            f"e{int(params.get('epochs', 0) or 0)}",
            f"b{int(params.get('batch_size', 0) or 0)}",
            f"lr{_learning_rate_fragment(params.get('learning_rate'))}",
            f"l{int(params.get('max_length', 0) or 0)}",
            "gold" if bool(params.get("include_gold_labels")) else "nogold",
            timestamp[-8:],
            unique_suffix,
        ]
        code = "-".join(filter(None, parts))
        if len(code) <= 64:
            return code
        compact_parts = [
            _sanitize_code_fragment(run.target_stage, fallback="stage"),
            _sanitize_code_fragment(model_type, fallback="model"),
            f"s{sample_count}",
            f"e{int(params.get('epochs', 0) or 0)}",
            f"b{int(params.get('batch_size', 0) or 0)}",
            timestamp[-8:],
            unique_suffix,
        ]
        compact_code = "-".join(filter(None, compact_parts))
        return compact_code[:64]


class _TorchCompetencyModel:
    def __init__(
        self,
        *,
        model_path: str,
        num_competencies: int,
        num_levels: int,
        batch_size: int,
        max_length: int,
        device: str = "auto",
        random_seed: int | None = None,
    ) -> None:
        import torch
        import torch.nn as nn
        from transformers import AutoModel, AutoTokenizer

        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        settings = get_settings()
        torch_threads = max(1, settings.active_learning_torch_threads)
        torch.set_num_threads(torch_threads)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass

        self.torch = torch
        self.nn = nn
        self.model_path = model_path
        self.num_competencies = num_competencies
        self.num_levels = num_levels
        self.batch_size = batch_size
        self.max_length = max_length
        if device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA was selected but is not available. Install a CUDA-enabled PyTorch build "
                "and confirm the NVIDIA driver is available, or choose CPU."
            )
        resolved_device = "cuda" if device == "auto" and torch.cuda.is_available() else device
        if resolved_device == "auto":
            resolved_device = "cpu"
        self.device = torch.device(resolved_device)
        self._train_generator = torch.Generator(device="cpu")
        if random_seed is not None:
            self._set_reproducible_mode(random_seed)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        backbone = AutoModel.from_pretrained(model_path)
        self.model = _FrozenBackboneClassifier(
            backbone,
            num_competencies,
            num_levels,
        ).to(self.device)

    def fit(
        self,
        train_examples: list[TrainingExample],
        val_examples: list[TrainingExample],
        *,
        epochs: int,
        learning_rate: float,
        patience: int,
        random_seed: int,
        epoch_callback,
        progress_callback=None,
    ) -> dict[str, float]:
        def log(message: str) -> None:
            if progress_callback is not None:
                progress_callback(message)

        self._set_reproducible_mode(random_seed)
        log(
            f"Reproducibility enabled: seed={random_seed}, "
            f"device={self.device}, deterministic_algorithms=True."
        )
        self.model.reset_classifier_weights()
        self.model.train()
        optimizer = self.torch.optim.AdamW(
            [param for param in self.model.parameters() if param.requires_grad],
            lr=learning_rate,
        )
        train_loader = self._loader(
            train_examples,
            include_labels=True,
            generator=self._train_generator,
        )
        val_loader = self._loader(val_examples or train_examples, include_labels=True)
        best_state = copy.deepcopy(self.model.state_dict())
        best_metrics: dict[str, float] = {"macro_f1": -1.0}
        early_stop_count = 0
        train_batch_count = len(train_loader)
        val_batch_count = len(val_loader)
        log(f"Prepared loaders: train_batches={train_batch_count}, validation_batches={val_batch_count}.")

        for epoch_no in range(1, epochs + 1):
            log(f"Epoch {epoch_no}/{epochs} started.")
            self.model.train()
            train_losses: list[float] = []
            for batch_no, (input_ids, attention_mask, labels) in enumerate(train_loader, start=1):
                optimizer.zero_grad()
                outputs = self.model(
                    input_ids.to(self.device),
                    attention_mask.to(self.device),
                    labels.to(self.device),
                )
                loss = outputs["loss"]
                loss.backward()
                optimizer.step()
                batch_loss = float(loss.detach().cpu().item())
                train_losses.append(batch_loss)
                log(
                    f"Epoch {epoch_no}/{epochs} train batch {batch_no}/{train_batch_count}: "
                    f"loss={batch_loss:.6f}."
                )

            log(f"Epoch {epoch_no}/{epochs} evaluating {val_batch_count} validation batches.")
            metrics = self._evaluate_loader(val_loader)
            metrics["train_loss"] = _safe_mean(train_losses)
            epoch_callback(epoch_no, metrics)
            log(
                f"Epoch {epoch_no}/{epochs} metrics: "
                f"train_loss={metrics.get('train_loss'):.6f}, "
                f"val_loss={metrics.get('val_loss'):.6f}, "
                f"accuracy={metrics.get('level_accuracy'):.6f}, "
                f"macro_f1={metrics.get('macro_f1'):.6f}, "
                f"detection={metrics.get('detection_rate'):.6f}."
            )

            if metrics["macro_f1"] > best_metrics.get("macro_f1", -1.0):
                best_metrics = metrics
                best_state = copy.deepcopy(self.model.state_dict())
                early_stop_count = 0
                log(f"Epoch {epoch_no}/{epochs} is the new best checkpoint.")
            else:
                early_stop_count += 1
                log(f"Epoch {epoch_no}/{epochs} did not improve; early_stop_count={early_stop_count}.")
            if early_stop_count >= patience:
                log(f"Early stopping triggered at epoch {epoch_no}.")
                break

        self.model.load_state_dict(best_state)
        log("Loaded best checkpoint weights into memory.")
        return best_metrics

    def _set_reproducible_mode(self, random_seed: int) -> None:
        torch = self.torch

        random.seed(random_seed)
        np.random.seed(random_seed)
        torch.manual_seed(random_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(random_seed)
            torch.cuda.manual_seed_all(random_seed)
        if hasattr(torch, "use_deterministic_algorithms"):
            torch.use_deterministic_algorithms(True)
        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.allow_tf32 = False
        if hasattr(torch.backends, "cuda") and hasattr(torch.backends.cuda, "matmul"):
            torch.backends.cuda.matmul.allow_tf32 = False
        self._train_generator.manual_seed(random_seed)

    def predict_proba(self, texts: list[str], *, progress_callback=None) -> np.ndarray:
        if not texts:
            if progress_callback is not None:
                progress_callback(0, 0)
            return np.empty((0, self.num_competencies, self.num_levels))
        self.model.eval()
        loader = self._loader_texts(texts)
        outputs = []
        processed_count = 0
        total_count = len(texts)
        with self.torch.no_grad():
            for input_ids, attention_mask in loader:
                result = self.model(input_ids.to(self.device), attention_mask.to(self.device))
                outputs.append(result["probabilities"].detach().cpu().numpy())
                processed_count += int(input_ids.shape[0])
                if progress_callback is not None:
                    progress_callback(processed_count, total_count)
        return np.concatenate(outputs, axis=0)

    def save_checkpoint(self, checkpoint_path: str, metadata: dict) -> None:
        self.torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "model_path": self.model_path,
                "num_competencies": self.num_competencies,
                "num_levels": self.num_levels,
                "max_length": self.max_length,
                "metadata": metadata,
            },
            checkpoint_path,
        )

    @classmethod
    def load_from_checkpoint(
        cls,
        checkpoint_path: str,
        *,
        batch_size: int,
    ) -> "_TorchCompetencyModel":
        import torch

        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        model = cls(
            model_path=checkpoint["model_path"],
            num_competencies=int(checkpoint["num_competencies"]),
            num_levels=int(checkpoint["num_levels"]),
            batch_size=batch_size,
            max_length=int(checkpoint["max_length"]),
            device="auto",
        )
        model.model.load_state_dict(checkpoint["model_state_dict"])
        model.model.to(model.device)
        model.model.eval()
        return model

    def _loader(
        self,
        examples: list[TrainingExample],
        *,
        include_labels: bool,
        generator=None,
    ):
        labels = [item.labels for item in examples]
        texts = [item.text for item in examples]
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        tensors = [encoded["input_ids"], encoded["attention_mask"]]
        if include_labels:
            tensors.append(self.torch.tensor(labels, dtype=self.torch.long))
        dataset = self.torch.utils.data.TensorDataset(*tensors)
        return self.torch.utils.data.DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=include_labels,
            generator=generator,
        )

    def _loader_texts(self, texts: list[str]):
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        dataset = self.torch.utils.data.TensorDataset(
            encoded["input_ids"],
            encoded["attention_mask"],
        )
        return self.torch.utils.data.DataLoader(dataset, batch_size=self.batch_size)

    def _evaluate_loader(self, loader) -> dict[str, float]:
        self.model.eval()
        val_losses: list[float] = []
        logits_list = []
        labels_list = []
        with self.torch.no_grad():
            for input_ids, attention_mask, labels in loader:
                outputs = self.model(
                    input_ids.to(self.device),
                    attention_mask.to(self.device),
                    labels.to(self.device),
                )
                val_losses.append(float(outputs["loss"].detach().cpu().item()))
                logits_list.append(outputs["logits"].detach().cpu().numpy())
                labels_list.append(labels.detach().cpu().numpy())
        logits = np.concatenate(logits_list, axis=0)
        labels = np.concatenate(labels_list, axis=0)
        preds = np.argmax(logits.reshape(-1, self.num_competencies, self.num_levels), axis=-1)
        flat_preds = preds.flatten()
        flat_labels = labels.flatten()
        return {
            "val_loss": _safe_mean(val_losses),
            "level_accuracy": _accuracy(flat_labels, flat_preds),
            "macro_f1": _macro_f1(flat_labels, flat_preds, self.num_levels),
            "detection_rate": _accuracy(
                (flat_labels > 0).astype(int),
                (flat_preds > 0).astype(int),
            ),
        }


class _FrozenBackboneClassifier:
    def __new__(cls, backbone, num_competencies: int, num_levels: int):
        import torch.nn as nn

        class Model(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.backbone = backbone
                for param in self.backbone.parameters():
                    param.requires_grad = False
                hidden_size = int(getattr(self.backbone.config, "hidden_size", 768))
                self.dropout = nn.Dropout(0.1)
                self.classifier = nn.Linear(hidden_size, num_competencies * num_levels)

            def reset_classifier_weights(self) -> None:
                nn.init.xavier_uniform_(self.classifier.weight)
                if self.classifier.bias is not None:
                    nn.init.zeros_(self.classifier.bias)

            def forward(self, input_ids, attention_mask=None, labels=None):
                import torch

                outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
                pooled = getattr(outputs, "pooler_output", None)
                if pooled is None:
                    pooled = outputs.last_hidden_state[:, 0]
                logits = self.classifier(self.dropout(pooled))
                reshaped = logits.view(-1, num_competencies, num_levels)
                probabilities = torch.softmax(reshaped, dim=-1)
                loss = None
                if labels is not None:
                    weights = torch.tensor([1.0, 5.0, 5.0, 5.0], device=logits.device)
                    loss_fn = nn.CrossEntropyLoss(weight=weights)
                    loss = loss_fn(logits.view(-1, num_levels), labels.view(-1))
                return {"loss": loss, "logits": logits, "probabilities": probabilities}

        return Model()


def _question_text(question: Question) -> str:
    content = question.content
    if content is None:
        return ""
    return "\n".join(
        part
        for part in [content.stem_text, content.answer_text, content.solution_text]
        if part
    )


def _labels_from_competencies(
    competencies: list[QuestionAggregateCompetency] | list[QuestionGoldCompetency],
    label_index: dict[int, int],
) -> list[int]:
    labels = [0] * len(label_index)
    for item in competencies:
        idx = label_index.get(item.competency_id)
        if idx is not None:
            labels[idx] = int(item.level_value)
    return labels


def _confidence_scores(probs: np.ndarray, strategy: str) -> tuple[float, float]:
    max_probs = np.max(probs, axis=-1)
    if strategy == "min_max_probability":
        confidence = float(np.min(max_probs))
        return confidence, 1.0 - confidence
    if strategy == "entropy":
        entropy = -np.sum(
            probs * np.log(np.clip(probs, 1e-12, 1.0)),
            axis=-1,
        ) / math.log(probs.shape[-1])
        uncertainty = float(np.mean(entropy))
        return 1.0 - uncertainty, uncertainty
    if strategy == "margin":
        sorted_probs = np.sort(probs, axis=-1)
        margins = sorted_probs[:, -1] - sorted_probs[:, -2]
        confidence = float(np.mean(margins))
        return confidence, 1.0 - confidence
    confidence = float(np.mean(max_probs))
    return confidence, 1.0 - confidence


def _accuracy(labels: np.ndarray, preds: np.ndarray) -> float:
    if labels.size == 0:
        return 0.0
    return float(np.mean(labels == preds))


def _macro_f1(labels: np.ndarray, preds: np.ndarray, num_classes: int) -> float:
    scores: list[float] = []
    for class_id in range(num_classes):
        true_positive = float(np.sum((preds == class_id) & (labels == class_id)))
        false_positive = float(np.sum((preds == class_id) & (labels != class_id)))
        false_negative = float(np.sum((preds != class_id) & (labels == class_id)))
        if true_positive == 0 and false_positive == 0 and false_negative == 0:
            scores.append(0.0)
            continue
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        score = 0.0 if precision + recall == 0 else (2 * precision * recall) / (precision + recall)
        scores.append(score)
    return _safe_mean(scores)


def _safe_mean(values) -> float:
    values = list(values)
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _candidate_snapshot_cutoff(
    candidates: list[CoresetCandidate],
    fallback: datetime | None,
) -> datetime | None:
    candidate_times = [item.created_at for item in candidates if item.created_at is not None]
    if candidate_times:
        return max(candidate_times)
    return fallback


def _snapshot_cutoff_from_run(run: ModelCoresetRun | None) -> datetime | None:
    if run is None:
        return None
    metrics = run.metrics_json or {}
    text_value = metrics.get("snapshot_created_before")
    if isinstance(text_value, str):
        try:
            return datetime.fromisoformat(text_value)
        except ValueError:
            pass
    return run.finished_at or run.created_at


def _default_coreset_selection_mode(strategy: str) -> str:
    if strategy == "kmeans":
        return "full_pool_embedding"
    if strategy in {"facility_location", "graph_cut", "moe"}:
        return "hierarchical_full_pool"
    if strategy == "random":
        return "full_pool_random"
    return "full_pool_selection"


def _coreset_phase_label(strategy: str, update_mode: str = "full") -> str:
    if update_mode == "incremental":
        if strategy == "kmeans":
            return "增量聚类更新中"
        if strategy in {"facility_location", "graph_cut", "moe"}:
            return "增量分层选题中"
        if strategy == "random":
            return "增量随机选题中"
        return "增量选题中"
    if strategy == "kmeans":
        return "全量向量聚类中"
    if strategy in {"facility_location", "graph_cut", "moe"}:
        return "分层全量选题中"
    if strategy == "random":
        return "全量随机选题中"
    return "全量选题中"


def _summary_int(summary: dict[str, int | float | str], key: str) -> int | None:
    value = summary.get(key)
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _metric_decimal(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(f"{float(value):.6f}")


def _decimal_to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None
