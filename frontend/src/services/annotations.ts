import { apiClient } from "@/services/api-client";
import type {
  AdminSelectionRequest,
  AdminSelectionResponse,
  AnnotationTaskListResponse,
  ClaimAnnotationRequest,
  ClaimAnnotationResponse,
  PoolSummaryResponse,
  SelectionStrategyItem,
  SubmitAnnotationRequest,
  SubmitAnnotationResponse,
} from "@/types/annotations";

export async function getAnnotationPoolSummary() {
  const response = await apiClient.get<PoolSummaryResponse>("/annotations/pools/summary");
  return response.data;
}

export async function getSelectionStrategies() {
  const response = await apiClient.get<SelectionStrategyItem[]>("/annotations/selection-strategies");
  return response.data;
}

export async function selectQuestionsForAnnotation(payload: AdminSelectionRequest) {
  const response = await apiClient.post<AdminSelectionResponse>("/annotations/admin/select", payload);
  return response.data;
}

export async function claimAnnotationTasks(payload: ClaimAnnotationRequest) {
  const response = await apiClient.post<ClaimAnnotationResponse>("/annotations/claim", payload);
  return response.data;
}

export async function getAnnotationTasks(params: {
  user_id: number;
  task_status?: string;
  page?: number;
  page_size?: number;
}) {
  const response = await apiClient.get<AnnotationTaskListResponse>("/annotations/tasks", { params });
  return response.data;
}

export async function submitAnnotationTask(taskId: number, payload: SubmitAnnotationRequest) {
  const response = await apiClient.post<SubmitAnnotationResponse>(
    `/annotations/tasks/${taskId}/submit`,
    payload,
  );
  return response.data;
}
