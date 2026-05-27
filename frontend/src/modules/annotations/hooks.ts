import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveAdminQuestionReview,
  claimReviewTasks,
  claimAnnotationTasks,
  getAnnotationPolicy,
  getAnnotatorHistory,
  getAdminQuestionReview,
  getSelectionBatches,
  getAnnotationPoolSummary,
  getAnnotationTasks,
  getReviewTasks,
  getSelectionStrategies,
  getWorkspaceSummary,
  overrideAdminQuestionReview,
  rejectAdminQuestionReview,
  reconcileReviewTasksWithCurrentRules,
  reviseAnnotationTask,
  resetAnnotationPools,
  rollbackSelectionBatch,
  selectQuestionsForAnnotation,
  submitAnnotationTask,
  submitReviewTask,
  updateAnnotationPolicy,
} from "@/services/annotations";
import type {
  AdminAggregateOverrideRequest,
  AnnotationPolicyUpdateRequest,
  AdminReviewDecisionRequest,
  AdminSelectionRequest,
  AdminSelectionResponse,
  AdminPoolResetRequest,
  AutoReconcileReviewTasksRequest,
  ClaimAnnotationRequest,
  ClaimReviewTaskRequest,
  PoolSummaryResponse,
  SelectionBatchRollbackRequest,
  SubmitAnnotationRequest,
  SubmitReviewTaskRequest,
} from "@/types/annotations";

export function useAnnotationPoolSummary() {
  return useQuery({
    queryKey: ["annotations", "pools", "summary"],
    queryFn: getAnnotationPoolSummary,
    refetchInterval: 3000,
  });
}

export function useAnnotationPolicy() {
  return useQuery({
    queryKey: ["annotations", "admin", "policy"],
    queryFn: getAnnotationPolicy,
    refetchInterval: 3000,
  });
}

export function useWorkspaceSummary(userId: number | null) {
  return useQuery({
    queryKey: ["annotations", "workspace-summary", userId],
    queryFn: () => getWorkspaceSummary(userId as number),
    enabled: userId !== null,
    refetchInterval: 3000,
  });
}

export function useSelectionStrategies() {
  return useQuery({
    queryKey: ["annotations", "selection-strategies"],
    queryFn: getSelectionStrategies,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSelectQuestionsForAnnotation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminSelectionRequest) => selectQuestionsForAnnotation(payload),
    onSuccess: (data) => {
      updatePoolSummaryAfterSelection(queryClient, data);
      queryClient.invalidateQueries({ queryKey: ["annotations", "selection-batches"] });
      queryClient.invalidateQueries({ queryKey: ["annotations", "pools", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["annotations", "tasks"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useSelectionBatches(limit = 20) {
  return useQuery({
    queryKey: ["annotations", "selection-batches", limit],
    queryFn: () => getSelectionBatches(limit),
    refetchInterval: 3000,
  });
}

export function useResetAnnotationPools() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminPoolResetRequest) => resetAnnotationPools(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useUpdateAnnotationPolicy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AnnotationPolicyUpdateRequest) => updateAnnotationPolicy(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useRollbackSelectionBatch() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      batchId,
      payload,
    }: {
      batchId: number;
      payload: SelectionBatchRollbackRequest;
    }) => rollbackSelectionBatch(batchId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

function updatePoolSummaryAfterSelection(
  queryClient: ReturnType<typeof useQueryClient>,
  data: AdminSelectionResponse,
) {
  if (data.moved_count <= 0) return;

  queryClient.setQueryData<PoolSummaryResponse>(
    ["annotations", "pools", "summary"],
    (current) => {
      if (!current) return current;
      return {
        items: current.items.map((item) => {
          if (item.status === "PENDING") {
            return { ...item, count: Math.max(0, item.count - data.moved_count) };
          }
          if (item.status === "WAITING") {
            return { ...item, count: item.count + data.moved_count };
          }
          return item;
        }),
      };
    },
  );
}

export function useClaimAnnotationTasks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClaimAnnotationRequest) => claimAnnotationTasks(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useAnnotationTasks(userId: number | null, taskStatus?: string) {
  return useQuery({
    queryKey: ["annotations", "tasks", userId, taskStatus],
    queryFn: () =>
      getAnnotationTasks({
        user_id: userId as number,
        task_status: taskStatus,
        page: 1,
        page_size: 50,
      }),
    enabled: userId !== null,
    refetchInterval: 3000,
  });
}

export function useAnnotatorHistory(
  annotatorUserId: number | null,
  params?: {
    page?: number;
    page_size?: number;
    keyword?: string;
    review_state?: "NOT_REQUIRED" | "PENDING" | "COMPLETED";
    adoption_status?: "PENDING" | "PASSED" | "OVERRIDDEN";
    time_range?: "7d" | "30d";
  },
) {
  return useQuery({
    queryKey: ["annotations", "history", annotatorUserId, params],
    queryFn: () =>
      getAnnotatorHistory({
        annotator_user_id: annotatorUserId as number,
        page: params?.page ?? 1,
        page_size: params?.page_size ?? 20,
        keyword: params?.keyword,
        review_state: params?.review_state,
        adoption_status: params?.adoption_status,
        time_range: params?.time_range,
      }),
    enabled: annotatorUserId !== null,
    refetchInterval: 3000,
  });
}

export function useSubmitAnnotationTask(taskId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubmitAnnotationRequest) =>
      submitAnnotationTask(taskId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useClaimReviewTasks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ClaimReviewTaskRequest) => claimReviewTasks(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useAutoReconcileReviewTasks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AutoReconcileReviewTasksRequest) =>
      reconcileReviewTasksWithCurrentRules(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useReviewTasks(reviewerUserId: number | null, reviewStatus?: string) {
  return useQuery({
    queryKey: ["annotations", "review-tasks", reviewerUserId, reviewStatus],
    queryFn: () =>
      getReviewTasks({
        reviewer_user_id: reviewerUserId as number,
        review_status: reviewStatus,
        page: 1,
        page_size: 50,
      }),
    enabled: reviewerUserId !== null,
    refetchInterval: 3000,
  });
}

export function useReviseAnnotationTask(taskId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubmitAnnotationRequest) =>
      reviseAnnotationTask(taskId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useSubmitReviewTask(taskId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubmitReviewTaskRequest) => submitReviewTask(taskId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useAdminQuestionReview(questionId: number | null, adminUserId: number | null) {
  return useQuery({
    queryKey: ["annotations", "admin", "question-review", questionId, adminUserId],
    queryFn: () => getAdminQuestionReview(questionId as number, adminUserId as number),
    enabled: questionId !== null && adminUserId !== null,
    refetchInterval: 3000,
  });
}

export function useApproveAdminQuestionReview(questionId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminReviewDecisionRequest) =>
      approveAdminQuestionReview(questionId as number, payload),
    onSuccess: (_data, _payload) => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useRejectAdminQuestionReview(questionId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminReviewDecisionRequest) =>
      rejectAdminQuestionReview(questionId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useOverrideAdminQuestionReview(questionId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminAggregateOverrideRequest) =>
      overrideAdminQuestionReview(questionId as number, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      queryClient.invalidateQueries({ queryKey: ["visualization"] });
      queryClient.invalidateQueries({ queryKey: ["label-insights"] });
    },
  });
}
