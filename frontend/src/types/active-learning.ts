export type TrainingRunStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";
export type PredictionRunStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";
export type CoresetRunStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";
export type ConfidenceStrategy =
  | "mean_max_probability"
  | "min_max_probability"
  | "entropy"
  | "margin";
export type ActiveLearningStage = "junior" | "senior";
export type CoresetStrategy =
  | "random"
  | "kmeans"
  | "facility_location"
  | "graph_cut"
  | "moe";
export type CoresetDataScope = "all" | "pending";
export type CoresetUpdateMode = "full" | "incremental";

export type TrainingRunCreateRequest = {
  triggered_by_user_id?: number | null;
  target_stage: ActiveLearningStage;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  val_size: number;
  patience: number;
  max_length: number;
  random_seed: number;
  include_gold_labels: boolean;
  min_train_samples: number;
  device: "auto" | "cpu" | "cuda";
};

export type TrainingEpoch = {
  id: number;
  training_run_id: number;
  epoch_no: number;
  train_loss?: number | null;
  val_loss?: number | null;
  level_accuracy?: number | null;
  macro_f1?: number | null;
  detection_rate?: number | null;
  created_at: string;
};

export type TrainingRun = {
  id: number;
  run_no: string;
  run_display_name: string;
  status: TrainingRunStatus;
  triggered_by_user_id?: number | null;
  base_model_path: string;
  target_stage: string;
  train_sample_count: number;
  val_sample_count: number;
  dataset_sample_count: number;
  model_type?: string | null;
  base_model_name?: string | null;
  parameter_summary: string;
  trend_group_key: string;
  related_model_version_id?: number | null;
  related_model_version_code?: string | null;
  related_model_display_name?: string | null;
  params_json?: Record<string, unknown> | null;
  metrics_json?: Record<string, number> | null;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  epochs: TrainingEpoch[];
};

export type TrainingRunLog = {
  run_id: number;
  log_text: string;
  stderr_text: string;
  is_truncated: boolean;
};

export type ModelVersion = {
  id: number;
  version_code: string;
  version_display_name: string;
  model_type?: string | null;
  base_model_name?: string | null;
  artifact_path?: string | null;
  training_run_id: number;
  source_run_no?: string | null;
  source_run_display_name?: string | null;
  checkpoint_path: string;
  is_active: boolean;
  level_accuracy?: number | null;
  macro_f1?: number | null;
  detection_rate?: number | null;
  val_loss?: number | null;
  train_sample_count: number;
  val_sample_count: number;
  dataset_sample_count: number;
  parameter_summary: string;
  trend_group_key: string;
  params_json?: Record<string, unknown> | null;
  created_at: string;
};

export type TrendPoint = {
  model_version_id: number;
  training_run_id: number;
  label: string;
  sample_label: string;
  sample_count: number;
  train_sample_count: number;
  val_sample_count: number;
  level_accuracy?: number | null;
  macro_f1?: number | null;
  detection_rate?: number | null;
  created_at: string;
};

export type TrendGroup = {
  key: string;
  label: string;
  parameter_summary: string;
  target_stage: string;
  model_type?: string | null;
  base_model_name?: string | null;
  point_count: number;
  points: TrendPoint[];
};

export type PredictionRunCreateRequest = {
  triggered_by_user_id?: number | null;
  model_version_id?: number | null;
  target_stage: ActiveLearningStage;
  select_count: number;
  confidence_strategy: ConfidenceStrategy;
  batch_size: number;
  auto_move_to_waiting: boolean;
};

export type PredictionItem = {
  id: number;
  prediction_run_id: number;
  question_id: number;
  predicted_levels_json: number[];
  confidence_score: number;
  uncertainty_score: number;
  rank_no: number;
  is_selected: boolean;
  created_at: string;
};

export type PredictionRun = {
  id: number;
  run_no: string;
  model_version_id: number;
  status: PredictionRunStatus;
  triggered_by_user_id?: number | null;
  confidence_strategy: ConfidenceStrategy;
  candidate_count: number;
  selected_count: number;
  moved_count: number;
  recommendation_batch_id?: number | null;
  params_json?: Record<string, unknown> | null;
  metrics_json?: Record<string, number | null> | null;
  error_message?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  items: PredictionItem[];
};

export type CoresetRunCreateRequest = {
  triggered_by_user_id?: number | null;
  strategy: CoresetStrategy;
  count: number;
  data_scope: CoresetDataScope;
  update_mode: CoresetUpdateMode;
};

export type CoresetIncrementalSummary = {
  can_run_incremental: boolean;
  data_scope: CoresetDataScope;
  baseline_run_id?: number | null;
  baseline_run_no?: string | null;
  baseline_batch_no?: string | null;
  baseline_strategy?: CoresetStrategy | null;
  baseline_finished_at?: string | null;
  baseline_selected_count: number;
  current_pool_count: number;
  new_unlabeled_count: number;
  incremental_candidate_count: number;
  anchor_count: number;
  snapshot_created_before?: string | null;
};

export type CoresetRun = {
  id: number;
  run_no: string;
  status: CoresetRunStatus;
  triggered_by_user_id?: number | null;
  strategy: CoresetStrategy;
  data_scope: CoresetDataScope;
  update_mode: CoresetUpdateMode;
  requested_count: number;
  candidate_count: number;
  selected_count: number;
  moved_count: number;
  recommendation_batch_id?: number | null;
  batch_no?: string | null;
  recommendation_batch_no?: string | null;
  params_json?: Record<string, unknown> | null;
  metrics_json?: Record<string, unknown> | null;
  error_message?: string | null;
  baseline_run_id?: number | null;
  baseline_run_no?: string | null;
  baseline_batch_no?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  created_at: string;
  question_ids: number[];
  moved_question_ids: number[];
};

export type ActiveLearningOverviewResponse = {
  active_model?: ModelVersion | null;
  model_versions: ModelVersion[];
  training_runs: TrainingRun[];
  prediction_runs: PredictionRun[];
  coreset_runs: CoresetRun[];
  coreset_incremental?: CoresetIncrementalSummary | null;
  coreset_incremental_by_strategy?: Record<string, CoresetIncrementalSummary>;
  trend_groups: TrendGroup[];
  completed_sample_count: number;
  pending_candidate_count: number;
};
