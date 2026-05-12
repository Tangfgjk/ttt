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
