import { apiClient } from "@/services/api-client";
import type {
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
