import { apiClient } from "@/services/api-client";
import type {
    AdminAggregateOverrideRequest,
  AnnotationPolicySettings,
  AnnotationPolicyUpdateRequest,
  AnnotationPolicyUpdateResponse,
  AdminQuestionReview,
  AdminPoolResetRequest,
  AdminPoolResetResponse,
  AdminReviewDecisionRequest,
  AdminSelectionRequest,
  AdminSelectionResponse,
  AnnotatorHistoryListResponse,
  AnnotationTaskListResponse,
  ClaimAnnotationRequest,
  ClaimAnnotationResponse,
  ClaimReviewTaskRequest,
  ClaimReviewTaskResponse,
  PoolSummaryResponse,
  ReviewTaskListResponse,
  SelectionBatchRollbackRequest,
  SelectionBatchRollbackResponse,
  SelectionBatchSummary,
  SelectionStrategyItem,
  SubmitAnnotationRequest,
  SubmitAnnotationResponse,
  SubmitReviewTaskRequest,
  SubmitReviewTaskResponse,
  WorkspaceSummary,
} from "@/types/annotations";

export async function getAnnotationPoolSummary() {
  const response = await apiClient.get<PoolSummaryResponse>("/annotations/pools/summary");
  return response.data;
}

export async function getAnnotationPolicy() {
  const response = await apiClient.get<AnnotationPolicySettings>("/annotations/admin/policy", {
    timeout: 60_000,
  });
  return response.data;
}

export async function updateAnnotationPolicy(payload: AnnotationPolicyUpdateRequest) {
  const response = await apiClient.post<AnnotationPolicyUpdateResponse>(
    "/annotations/admin/policy",
    payload,
    { timeout: 60_000 },
  );
  return response.data;
}

export async function getWorkspaceSummary(userId: number) {
  const response = await apiClient.get<WorkspaceSummary>("/annotations/workspace-summary", {
    params: { user_id: userId },
  });
  return response.data;
}

export async function getSelectionStrategies() {
  const response = await apiClient.get<SelectionStrategyItem[]>("/annotations/selection-strategies");
  return response.data;
}

export async function selectQuestionsForAnnotation(payload: AdminSelectionRequest) {
  const response = await apiClient.post<AdminSelectionResponse>(
    "/annotations/admin/select",
    payload,
    { timeout: 60_000 },
  );
  return response.data;
}

export async function getSelectionBatches(limit = 20) {
  const response = await apiClient.get<SelectionBatchSummary[]>("/annotations/admin/selection-batches", {
    params: { limit },
  });
  return response.data;
}

export async function resetAnnotationPools(payload: AdminPoolResetRequest) {
  const response = await apiClient.post<AdminPoolResetResponse>(
    "/annotations/admin/pools/reset",
    payload,
  );
  return response.data;
}

export async function rollbackSelectionBatch(
  batchId: number,
  payload: SelectionBatchRollbackRequest,
) {
  const response = await apiClient.post<SelectionBatchRollbackResponse>(
    `/annotations/admin/selection-batches/${batchId}/rollback`,
    payload,
  );
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

export async function getAnnotatorHistory(params: {
  annotator_user_id: number;
  page?: number;
  page_size?: number;
  keyword?: string;
  review_state?: "NOT_REQUIRED" | "PENDING" | "COMPLETED";
  adoption_status?: "PENDING" | "PASSED" | "OVERRIDDEN";
  time_range?: "7d" | "30d";
}) {
  const response = await apiClient.get<AnnotatorHistoryListResponse>("/annotations/history", {
    params,
  });
  return response.data;
}

export async function submitAnnotationTask(taskId: number, payload: SubmitAnnotationRequest) {
  const response = await apiClient.post<SubmitAnnotationResponse>(
    `/annotations/tasks/${taskId}/submit`,
    payload,
  );
  return response.data;
}

export async function reviseAnnotationTask(taskId: number, payload: SubmitAnnotationRequest) {
  const response = await apiClient.post<SubmitAnnotationResponse>(
    `/annotations/tasks/${taskId}/revise`,
    payload,
  );
  return response.data;
}

export async function claimReviewTasks(payload: ClaimReviewTaskRequest) {
  const response = await apiClient.post<ClaimReviewTaskResponse>(
    "/annotations/review-tasks/claim",
    payload,
  );
  return response.data;
}

export async function getReviewTasks(params: {
  reviewer_user_id: number;
  review_status?: string;
  page?: number;
  page_size?: number;
}) {
  const response = await apiClient.get<ReviewTaskListResponse>("/annotations/review-tasks", {
    params,
  });
  return response.data;
}

export async function submitReviewTask(taskId: number, payload: SubmitReviewTaskRequest) {
  const response = await apiClient.post<SubmitReviewTaskResponse>(
    `/annotations/review-tasks/${taskId}/submit`,
    payload,
  );
  return response.data;
}

export async function getAdminQuestionReview(questionId: number, adminUserId: number) {
  const response = await apiClient.get<AdminQuestionReview>(
    `/annotations/admin/questions/${questionId}/review`,
    {
      params: { admin_user_id: adminUserId },
    },
  );
  return response.data;
}

export async function approveAdminQuestionReview(
  questionId: number,
  payload: AdminReviewDecisionRequest,
) {
  const response = await apiClient.post<AdminQuestionReview>(
    `/annotations/admin/questions/${questionId}/approve`,
    payload,
  );
  return response.data;
}

export async function rejectAdminQuestionReview(
  questionId: number,
  payload: AdminReviewDecisionRequest,
) {
  const response = await apiClient.post<AdminQuestionReview>(
    `/annotations/admin/questions/${questionId}/reject`,
    payload,
  );
  return response.data;
}

export async function overrideAdminQuestionReview(
  questionId: number,
  payload: AdminAggregateOverrideRequest,
) {
  const response = await apiClient.post<AdminQuestionReview>(
    `/annotations/admin/questions/${questionId}/override`,
    payload,
  );
  return response.data;
}
