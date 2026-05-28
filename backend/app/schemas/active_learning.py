from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TrainingRunStatus = Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"]
PredictionRunStatus = Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"]
CoresetRunStatus = Literal["PENDING", "RUNNING", "SUCCESS", "FAILED"]
ActiveLearningStage = Literal["junior", "senior"]
ConfidenceStrategy = Literal["mean_max_probability", "min_max_probability", "entropy", "margin"]
TrainingDevice = Literal["auto", "cpu", "cuda"]
SelectionStrategy = Literal["random", "kmeans", "facility_location", "graph_cut", "moe"]
SelectionDataScope = Literal["all", "pending"]
CoresetUpdateMode = Literal["full", "incremental"]


class TrainingRunCreateRequest(BaseModel):
    triggered_by_user_id: int | None = None
    target_stage: ActiveLearningStage = "junior"
    epochs: int = Field(default=20, ge=1, le=50)
    batch_size: int = Field(default=16, ge=1, le=128)
    learning_rate: float = Field(default=5e-5, gt=0, le=1)
    val_size: float = Field(default=0.2, ge=0.05, le=0.5)
    patience: int = Field(default=5, ge=1, le=50)
    max_length: int = Field(default=256, ge=32, le=512)
    random_seed: int = Field(default=42, ge=0, le=1_000_000)
    include_gold_labels: bool = False
    min_train_samples: int = Field(default=5, ge=1, le=10000)
    device: TrainingDevice = "auto"
    max_coreset_round: int | None = Field(default=None, ge=1)


class TrainingEpochOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    training_run_id: int
    epoch_no: int
    train_loss: float | None = None
    val_loss: float | None = None
    level_accuracy: float | None = None
    macro_f1: float | None = None
    detection_rate: float | None = None
    created_at: datetime


class TrainingRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_no: str
    status: TrainingRunStatus
    triggered_by_user_id: int | None = None
    base_model_path: str
    target_stage: str
    train_sample_count: int
    val_sample_count: int
    dataset_sample_count: int
    run_display_name: str
    model_type: str | None = None
    base_model_name: str | None = None
    parameter_summary: str
    trend_group_key: str
    related_model_version_id: int | None = None
    related_model_version_code: str | None = None
    related_model_display_name: str | None = None
    params_json: dict | None = None
    metrics_json: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    epochs: list[TrainingEpochOut] = Field(default_factory=list)


class TrainingRunLogOut(BaseModel):
    run_id: int
    log_text: str
    stderr_text: str = ""
    is_truncated: bool = False


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version_code: str
    version_display_name: str
    model_type: str | None = None
    base_model_name: str | None = None
    artifact_path: str | None = None
    training_run_id: int
    source_run_no: str | None = None
    source_run_display_name: str | None = None
    checkpoint_path: str
    is_active: bool
    level_accuracy: float | None = None
    macro_f1: float | None = None
    detection_rate: float | None = None
    val_loss: float | None = None
    train_sample_count: int
    val_sample_count: int
    dataset_sample_count: int
    parameter_summary: str
    trend_group_key: str
    params_json: dict | None = None
    created_at: datetime


class TrendPointOut(BaseModel):
    model_version_id: int
    training_run_id: int
    label: str
    sample_label: str
    sample_count: int
    train_sample_count: int
    val_sample_count: int
    level_accuracy: float | None = None
    macro_f1: float | None = None
    detection_rate: float | None = None
    created_at: datetime


class TrendGroupOut(BaseModel):
    key: str
    label: str
    parameter_summary: str
    target_stage: str
    model_type: str | None = None
    base_model_name: str | None = None
    point_count: int
    points: list[TrendPointOut] = Field(default_factory=list)


class PredictionRunCreateRequest(BaseModel):
    triggered_by_user_id: int | None = None
    model_version_id: int | None = None
    target_stage: ActiveLearningStage = "junior"
    select_count: int = Field(default=100, ge=1, le=5000)
    confidence_strategy: ConfidenceStrategy = "mean_max_probability"
    batch_size: int = Field(default=32, ge=1, le=256)
    auto_move_to_waiting: bool = True


class PredictionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction_run_id: int
    question_id: int
    predicted_levels_json: list[int]
    confidence_score: float
    uncertainty_score: float
    rank_no: int
    is_selected: bool
    created_at: datetime


class PredictionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_no: str
    model_version_id: int
    status: PredictionRunStatus
    triggered_by_user_id: int | None = None
    confidence_strategy: str
    candidate_count: int
    selected_count: int
    moved_count: int
    recommendation_batch_id: int | None = None
    params_json: dict | None = None
    metrics_json: dict | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    items: list[PredictionItemOut] = Field(default_factory=list)


class CoresetRunCreateRequest(BaseModel):
    triggered_by_user_id: int | None = None
    strategy: SelectionStrategy = "kmeans"
    count: int = Field(default=400, ge=1, le=5000)
    data_scope: SelectionDataScope = "pending"
    update_mode: CoresetUpdateMode = "full"


class CoresetIncrementalSummaryOut(BaseModel):
    can_run_incremental: bool
    data_scope: SelectionDataScope = "pending"
    baseline_run_id: int | None = None
    baseline_run_no: str | None = None
    baseline_batch_no: str | None = None
    baseline_strategy: SelectionStrategy | None = None
    baseline_finished_at: datetime | None = None
    baseline_selected_count: int = 0
    current_pool_count: int = 0
    new_unlabeled_count: int = 0
    incremental_candidate_count: int = 0
    anchor_count: int = 0
    snapshot_created_before: datetime | None = None


class CoresetRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_no: str
    status: CoresetRunStatus
    triggered_by_user_id: int | None = None
    strategy: SelectionStrategy
    data_scope: SelectionDataScope
    update_mode: CoresetUpdateMode = "full"
    requested_count: int
    candidate_count: int
    selected_count: int
    moved_count: int
    recommendation_batch_id: int | None = None
    batch_no: str | None = None
    recommendation_batch_no: str | None = None
    params_json: dict | None = None
    metrics_json: dict | None = None
    error_message: str | None = None
    baseline_run_id: int | None = None
    baseline_run_no: str | None = None
    baseline_batch_no: str | None = None
    active_learning_round: int | None = None
    round_completed_count: int = 0
    round_unfinished_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    question_ids: list[int] = Field(default_factory=list)
    moved_question_ids: list[int] = Field(default_factory=list)


class ActiveLearningOverviewResponse(BaseModel):
    active_model: ModelVersionOut | None = None
    model_versions: list[ModelVersionOut]
    training_runs: list[TrainingRunOut]
    prediction_runs: list[PredictionRunOut]
    coreset_runs: list[CoresetRunOut] = Field(default_factory=list)
    coreset_incremental: CoresetIncrementalSummaryOut | None = None
    coreset_incremental_by_strategy: dict[str, CoresetIncrementalSummaryOut] = Field(default_factory=dict)
    trend_groups: list[TrendGroupOut] = Field(default_factory=list)
    completed_sample_count: int
    pending_candidate_count: int
