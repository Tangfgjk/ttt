import { apiClient } from "@/services/api-client";
import type {
  TrainingModuleResponse,
  TrainingStage,
  TrainingStatusResponse,
  TrainingSubmitRequest,
  TrainingSubmitResponse,
} from "@/types/training";

export async function getTrainingStatus(userId: number) {
  const response = await apiClient.get<TrainingStatusResponse>("/training/status", {
    params: { user_id: userId },
  });
  return response.data;
}

export async function getTrainingModule(userId: number, stage: TrainingStage) {
  const response = await apiClient.get<TrainingModuleResponse>(`/training/modules/${stage}`, {
    params: { user_id: userId },
  });
  return response.data;
}

export async function submitTraining(payload: TrainingSubmitRequest) {
  const response = await apiClient.post<TrainingSubmitResponse>("/training/submit", payload);
  return response.data;
}
