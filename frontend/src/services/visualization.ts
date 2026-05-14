import { apiClient } from "@/services/api-client";
import type {
  AnnotatedOverview,
  AnnotatedQuestionListResponse,
  EmbeddingRebuildResponse,
  EmbeddingStatus,
  QuestionDistribution,
  VisualizationMethod,
} from "@/types/visualization";

export async function getEmbeddingStatus() {
  const response = await apiClient.get<EmbeddingStatus>("/visualization/embedding-status");
  return response.data;
}

export async function getQuestionDistribution(params: {
  method: VisualizationMethod;
  status: string;
  limit?: number;
}) {
  const response = await apiClient.get<QuestionDistribution>("/visualization/question-distribution", {
    params,
    timeout: 120_000,
  });
  return response.data;
}

export async function rebuildMissingEmbeddings(limit?: number) {
  const response = await apiClient.post<EmbeddingRebuildResponse>(
    "/visualization/embeddings/rebuild",
    { limit },
    { timeout: 300_000 },
  );
  return response.data;
}

export async function getAnnotatedOverview(params?: {
  keyword?: string;
  subject_id?: number;
  grade_id?: number;
  edu_stage?: string;
  question_type_id?: number;
  result_source?: string;
}) {
  const response = await apiClient.get<AnnotatedOverview>("/visualization/annotated-overview", {
    params,
  });
  return response.data;
}

export async function getAnnotatedQuestions(params: {
  keyword?: string;
  subject_id?: number;
  grade_id?: number;
  edu_stage?: string;
  question_type_id?: number;
  result_source?: string;
  page?: number;
  page_size?: number;
}) {
  const response = await apiClient.get<AnnotatedQuestionListResponse>(
    "/visualization/annotated-questions",
    {
      params,
    },
  );
  return response.data;
}
