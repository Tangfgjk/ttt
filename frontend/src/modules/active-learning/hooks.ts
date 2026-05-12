import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  activateModelVersion,
  cancelCoresetRun,
  cancelPredictionRun,
  cancelTrainingRun,
  getActiveLearningOverview,
  getTrainingRunLogs,
  startCoresetRun,
  startPredictionRun,
  startTrainingRun,
} from "@/services/active-learning";
import type {
  CoresetRunCreateRequest,
  PredictionRunCreateRequest,
  TrainingRunCreateRequest,
} from "@/types/active-learning";

export function useActiveLearningOverview() {
  return useQuery({
    queryKey: ["active-learning", "overview"],
    queryFn: getActiveLearningOverview,
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasRunning =
        data?.training_runs.some((item) => ["PENDING", "RUNNING"].includes(item.status)) ||
        data?.prediction_runs.some((item) => ["PENDING", "RUNNING"].includes(item.status)) ||
        data?.coreset_runs.some((item) => ["PENDING", "RUNNING"].includes(item.status));
      return hasRunning ? 3000 : false;
    },
  });
}

export function useStartTrainingRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TrainingRunCreateRequest) => startTrainingRun(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}

export function useTrainingRunLogs(runId?: number | null, enabled = true) {
  return useQuery({
    queryKey: ["active-learning", "training-run-logs", runId],
    queryFn: () => getTrainingRunLogs(runId as number),
    enabled: enabled && typeof runId === "number",
    refetchInterval: enabled ? 2000 : false,
  });
}

export function useCancelTrainingRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => cancelTrainingRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}

export function useStartPredictionRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PredictionRunCreateRequest) => startPredictionRun(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useCancelPredictionRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => cancelPredictionRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useStartCoresetRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CoresetRunCreateRequest) => startCoresetRun(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useCancelCoresetRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: number) => cancelCoresetRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
      queryClient.invalidateQueries({ queryKey: ["annotations"] });
      queryClient.invalidateQueries({ queryKey: ["questions"] });
    },
  });
}

export function useActivateModelVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modelVersionId: number) => activateModelVersion(modelVersionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}
