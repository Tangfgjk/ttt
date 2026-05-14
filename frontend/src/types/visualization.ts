export type VisualizationMethod = "pca" | "tsne" | "umap";

export type EmbeddingStatus = {
  model_code: string;
  model_name: string;
  dimension: number;
  model_path: string;
  model_available: boolean;
  total_questions: number;
  embedded_questions: number;
  missing_embeddings: number;
};

export type DistributionPoint = {
  question_id: number;
  x: number;
  y: number;
  annotation_status: string;
  annotation_count: number;
  required_annotations: number;
  stem_preview: string;
};

export type QuestionDistribution = {
  method: string;
  requested_method: string;
  model_code: string;
  embedding_count: number;
  missing_embedding_count: number;
  summary: Record<string, number>;
  points: DistributionPoint[];
};

export type EmbeddingRebuildResponse = {
  created: number;
  skipped: number;
  failed: number;
};

export type AnnotatedDistributionBucket = {
  key: string;
  label: string;
  count: number;
};

export type AnnotatedOverview = {
  total_labeled_questions: number;
  filtered_question_count: number;
  gold_labeled_questions: number;
  aggregate_labeled_questions: number;
  total_completed_questions: number;
  disputed_questions: number;
  average_agreement_score?: number | null;
  cognitive_level_distribution: AnnotatedDistributionBucket[];
  competency_distribution: AnnotatedDistributionBucket[];
  competency_level_distribution: AnnotatedDistributionBucket[];
  grade_distribution: AnnotatedDistributionBucket[];
};

export type AnnotatedQuestionCompetency = {
  competency_id: number;
  competency_name: string;
  level_value: number;
  agreement_score?: number | null;
};

export type AnnotatedQuestionListItem = {
  question_id: number;
  stem_preview: string;
  subject_name: string;
  grade_name?: string | null;
  edu_stage?: string | null;
  question_type_name?: string | null;
  annotation_status: string;
  result_source: string;
  result_source_label: string;
  final_cognitive_level_id?: number | null;
  final_cognitive_level_name?: string | null;
  agreement_score?: number | null;
  completed_annotation_count: number;
  finalized_at?: string | null;
  competencies: AnnotatedQuestionCompetency[];
};

export type AnnotatedQuestionListResponse = {
  items: AnnotatedQuestionListItem[];
  meta: {
    page: number;
    page_size: number;
    total: number;
  };
};
