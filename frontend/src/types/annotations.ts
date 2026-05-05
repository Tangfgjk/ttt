import type { PageMeta, QuestionListItem } from "@/types/question";

export type AnnotationPoolStatus =
  | "PENDING"
  | "WAITING"
  | "IN_PROGRESS"
  | "REVIEW_PENDING"
  | "COMPLETED";

export type SelectionStrategy = "random" | "kmeans" | "facility_location" | "graph_cut" | "moe";

export type PoolSummaryItem = {
  status: AnnotationPoolStatus;
  count: number;
};

export type PoolSummaryResponse = {
  items: PoolSummaryItem[];
};

export type SelectionStrategyItem = {
  code: SelectionStrategy;
  name: string;
  description: string;
};

export type AdminSelectionRequest = {
  strategy: SelectionStrategy;
  count: number;
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
};

export type ClaimAnnotationRequest = {
  annotator_user_id: number;
  count: number;
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
