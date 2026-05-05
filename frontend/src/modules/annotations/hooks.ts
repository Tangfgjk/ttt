import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  claimAnnotationTasks,
  getAnnotationPoolSummary,
  getAnnotationTasks,
  getSelectionStrategies,
  selectQuestionsForAnnotation,
  submitAnnotationTask,
} from "@/services/annotations";
import type {
  AdminSelectionRequest,
  ClaimAnnotationRequest,
  SubmitAnnotationRequest,
} from "@/types/annotations";

export function useAnnotationPoolSummary() {
  return useQuery({
    queryKey: ["annotations", "pools", "summary"],
    queryFn: getAnnotationPoolSummary,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
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
