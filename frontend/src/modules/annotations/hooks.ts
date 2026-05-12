import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveAdminQuestionReview,
  claimReviewTasks,
  claimAnnotationTasks,
  getAnnotatorHistory,
  getAdminQuestionReview,
  getSelectionBatches,
  getAnnotationPoolSummary,
  getAnnotationTasks,
  getReviewTasks,
  getSelectionStrategies,
  getWorkspaceSummary,
  rejectAdminQuestionReview,
  resetAnnotationPools,
  rollbackSelectionBatch,
  selectQuestionsForAnnotation,
  submitAnnotationTask,
  submitReviewTask,
} from "@/services/annotations";
import type {
  AdminReviewDecisionRequest,
  AdminSelectionRequest,
  AdminSelectionResponse,
  AdminPoolResetRequest,
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

export function useAnnotatorHistory(annotatorUserId: number | null) {
  return useQuery({
    queryKey: ["annotations", "history", annotatorUserId],
    queryFn: () =>
      getAnnotatorHistory({
        annotator_user_id: annotatorUserId as number,
        page: 1,
        page_size: 50,
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
