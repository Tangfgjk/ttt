import { apiClient } from "@/services/api-client";
import type {
  ActiveLearningOverviewResponse,
  CoresetRun,
  CoresetRunCreateRequest,
  ModelVersion,
  PredictionRun,
  PredictionRunCreateRequest,
  TrainingRunLog,
  TrainingRun,
  TrainingRunCreateRequest,
} from "@/types/active-learning";

export async function getActiveLearningOverview() {
  const response = await apiClient.get<ActiveLearningOverviewResponse>("/active-learning/overview");
  return response.data;
}

export async function startTrainingRun(payload: TrainingRunCreateRequest) {
  const response = await apiClient.post<TrainingRun>("/active-learning/training-runs", payload);
  return response.data;
}

export async function getTrainingRuns() {
  const response = await apiClient.get<TrainingRun[]>("/active-learning/training-runs");
  return response.data;
}

export async function getTrainingRunLogs(runId: number) {
  const response = await apiClient.get<TrainingRunLog>(
    `/active-learning/training-runs/${runId}/logs`,
  );
  return response.data;
}

export async function cancelTrainingRun(runId: number) {
  const response = await apiClient.post<TrainingRun>(
    `/active-learning/training-runs/${runId}/cancel`,
  );
  return response.data;
}

export async function activateModelVersion(modelVersionId: number) {
  const response = await apiClient.post<ModelVersion>(
    `/active-learning/model-versions/${modelVersionId}/activate`,
  );
  return response.data;
}

export async function startPredictionRun(payload: PredictionRunCreateRequest) {
  const response = await apiClient.post<PredictionRun>("/active-learning/prediction-runs", payload);
  return response.data;
}

export async function cancelPredictionRun(runId: number) {
  const response = await apiClient.post<PredictionRun>(
    `/active-learning/prediction-runs/${runId}/cancel`,
  );
  return response.data;
}

export async function getPredictionRuns() {
  const response = await apiClient.get<PredictionRun[]>("/active-learning/prediction-runs");
  return response.data;
}

export async function startCoresetRun(payload: CoresetRunCreateRequest) {
  const response = await apiClient.post<CoresetRun>("/active-learning/coreset-runs", payload);
  return response.data;
}

export async function cancelCoresetRun(runId: number) {
  const response = await apiClient.post<CoresetRun>(
    `/active-learning/coreset-runs/${runId}/cancel`,
  );
  return response.data;
}

export async function getCoresetRuns() {
  const response = await apiClient.get<CoresetRun[]>("/active-learning/coreset-runs");
  return response.data;
}
