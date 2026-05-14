import type { PageMeta, QuestionListItem } from "@/types/question";

export type AnnotationPoolStatus =
  | "PENDING"
  | "WAITING"
  | "IN_PROGRESS"
  | "REVIEW_PENDING"
  | "COMPLETED";

export type SelectionStrategy = "random" | "kmeans" | "facility_location" | "graph_cut" | "moe";
export type SelectionDataScope = "all" | "pending";

export type PoolSummaryItem = {
  status: AnnotationPoolStatus;
  count: number;
};

export type PoolSummaryResponse = {
  items: PoolSummaryItem[];
};

export type WorkspaceSummary = {
  user_id: number;
  role: string;
  pending_task_count: number;
  completed_today_count: number;
  escalated_count: number;
  completed_review_count: number;
};

export type SelectionStrategyItem = {
  code: SelectionStrategy;
  name: string;
  description: string;
};

export type AdminSelectionRequest = {
  strategy: SelectionStrategy;
  count: number;
  data_scope: SelectionDataScope;
  triggered_by_user_id?: number | null;
};

export type AdminSelectionResponse = {
  batch_id: number;
  batch_no: string;
  strategy: SelectionStrategy;
  requested_count: number;
  selected_count: number;
  moved_count: number;
  candidate_count: number;
  question_ids: number[];
   moved_question_ids: number[];
};

export type SelectionBatchSummary = {
  id: number;
  batch_no: string;
  algorithm_code: string;
  triggered_by_user_id?: number | null;
  created_at: string;
  requested_count: number;
  candidate_count: number;
  selected_count: number;
  pending_count: number;
  waiting_count: number;
  in_progress_count: number;
   question_ids: number[];
};

export type AdminPoolResetRequest = {
  admin_user_id: number;
};

export type AdminPoolResetResponse = {
  recalled_in_progress_count: number;
  returned_waiting_count: number;
  reset_to_pending_count: number;
};

export type SelectionBatchRollbackRequest = {
  admin_user_id: number;
};

export type SelectionBatchRollbackResponse = {
  batch_id: number;
  batch_no: string;
  recalled_in_progress_count: number;
  returned_waiting_count: number;
  reset_to_pending_count: number;
};

export type ClaimAnnotationRequest = {
  annotator_user_id: number;
  count: number;
};

export type AnnotationTaskProgress = {
  submitted_annotation_count: number;
  active_annotation_count: number;
  required_annotations: number;
  remaining_annotation_count: number;
  progress_percent: number;
};

export type AnnotationTask = {
  id: number;
  question_id: number;
  assignee_id: number;
  source_batch_id?: number | null;
  task_status: string;
  assigned_at: string;
  started_at?: string | null;
  submitted_at?: string | null;
  question: QuestionListItem;
  progress: AnnotationTaskProgress;
};

export type ClaimAnnotationResponse = {
  claimed_count: number;
  task_ids: number[];
  items: AnnotationTask[];
};

export type AnnotationTaskListResponse = {
  items: AnnotationTask[];
  meta: PageMeta;
};

export type AnnotatorHistoryItem = {
  annotation_id: number;
  task_id?: number | null;
  question_id: number;
  submitted_at: string;
  confidence_level?: number | null;
  question_status: AnnotationPoolStatus;
  review_state: "NOT_REQUIRED" | "PENDING" | "COMPLETED";
  adoption_status: "PENDING" | "PASSED" | "OVERRIDDEN";
  question: QuestionListItem;
  annotation: ReviewAnnotation;
  final_aggregate?: AnnotationAggregate | null;
  review_logs: AnnotationReviewLog[];
};

export type AnnotatorHistoryListResponse = {
  items: AnnotatorHistoryItem[];
  meta: PageMeta;
};

export type AnnotationCompetencyInput = {
  competency_id: number;
  level_value: number;
};

export type SubmitAnnotationRequest = {
  annotator_user_id: number;
  cognitive_level_id?: number | null;
  competencies: AnnotationCompetencyInput[];
  confidence_level?: number | null;
  time_spent_seconds?: number | null;
};

export type SubmitAnnotationResponse = {
  annotation_id: number;
  question_id: number;
  annotation_count: number;
  required_annotations: number;
  question_status: AnnotationPoolStatus;
  aggregate_id?: number | null;
  is_disputed: boolean;
};

export type ClaimReviewTaskRequest = {
  reviewer_user_id: number;
  count: number;
};

export type AnnotationAggregateCompetency = {
  competency_id: number;
  competency_name: string;
  level_value: number;
  agreement_score?: number | null;
};

export type AnnotationAggregate = {
  id: number;
  question_id: number;
  final_cognitive_level_id?: number | null;
  agreement_score?: number | null;
  is_disputed: boolean;
  completed_annotation_count: number;
  finalized_at?: string | null;
  competencies: AnnotationAggregateCompetency[];
};

export type ReviewAnnotationCompetency = {
  competency_id: number;
  competency_name: string;
  level_value: number;
};

export type ReviewAnnotation = {
  annotation_id: number;
  user_id: number;
  user_name: string;
  cognitive_level_id?: number | null;
  confidence_level?: number | null;
  submitted_at: string;
  competencies: ReviewAnnotationCompetency[];
};

export type AnnotationConsensusVote = {
  level_value?: number | null;
  vote_count: number;
  annotator_names: string[];
  weighted_score?: number | null;
};

export type AnnotationConsensusDimension = {
  dimension_type: "cognitive_level" | "competency";
  dimension_key: string;
  dimension_label: string;
  recommended_level_value?: number | null;
  agreement_score: number;
  consensus_status: "UNANIMOUS" | "MAJORITY" | "DISPUTED";
  vote_summary: AnnotationConsensusVote[];
};

export type AnnotationConsensusSummary = {
  agreement_score?: number | null;
  consensus_status: "UNANIMOUS" | "MAJORITY" | "DISPUTED" | "INSUFFICIENT";
  completed_annotation_count: number;
  required_annotations: number;
  unresolved_dimension_count: number;
  dimensions: AnnotationConsensusDimension[];
};

export type AnnotationReviewLog = {
  id: number;
  question_id: number;
  aggregate_id?: number | null;
  review_task_id?: number | null;
  actor_user_id?: number | null;
  actor_name?: string | null;
  actor_role?: string | null;
  action_code: string;
  action_label: string;
  comment?: string | null;
  detail_json?: Record<string, unknown> | null;
  created_at: string;
};

export type ReviewTask = {
  id: number;
  question_id: number;
  aggregate_id: number;
  reviewer_id?: number | null;
  review_status: string;
  review_comment?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  question: QuestionListItem;
  aggregate: AnnotationAggregate;
  annotations: ReviewAnnotation[];
  consensus: AnnotationConsensusSummary;
  review_logs: AnnotationReviewLog[];
};

export type ClaimReviewTaskResponse = {
  claimed_count: number;
  task_ids: number[];
  items: ReviewTask[];
};

export type ReviewTaskListResponse = {
  items: ReviewTask[];
  meta: PageMeta;
};

export type SubmitReviewTaskRequest = {
  reviewer_user_id: number;
  cognitive_level_id?: number | null;
  competencies: AnnotationCompetencyInput[];
  review_comment?: string | null;
};

export type SubmitReviewTaskResponse = {
  review_task_id: number;
  question_id: number;
  aggregate_id: number;
  review_status: string;
  question_status: AnnotationPoolStatus;
};

export type AdminQuestionAnnotation = {
  annotation_id: number;
  task_id?: number | null;
  task_status?: string | null;
  user_id: number;
  user_name: string;
  cognitive_level_id?: number | null;
  confidence_level?: number | null;
  submitted_at: string;
  competencies: ReviewAnnotationCompetency[];
};

export type AdminQuestionReview = {
  question_id: number;
  annotation_status: AnnotationPoolStatus;
  submitted_annotation_count: number;
  active_annotation_count: number;
  required_annotations: number;
  remaining_annotation_count: number;
  open_review_task_count: number;
  aggregate?: AnnotationAggregate | null;
  gold_label?: AnnotationAggregate | null;
  consensus: AnnotationConsensusSummary;
  annotations: AdminQuestionAnnotation[];
  review_logs: AnnotationReviewLog[];
};

export type AdminReviewDecisionRequest = {
  admin_user_id: number;
  review_comment?: string | null;
  additional_annotations?: number;
};

export type AdminAggregateOverrideRequest = {
  admin_user_id: number;
  final_cognitive_level_id?: number | null;
  competencies: AnnotationCompetencyInput[];
  review_comment?: string | null;
};
