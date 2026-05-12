import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getTrainingModule, getTrainingStatus, submitTraining } from "@/services/training";
import type { TrainingStage, TrainingSubmitRequest } from "@/types/training";

export function useTrainingStatus(userId: number | null) {
  return useQuery({
    queryKey: ["training", "status", userId],
    queryFn: () => getTrainingStatus(userId as number),
    enabled: userId !== null,
  });
}

export function useTrainingModule(userId: number | null, stage: TrainingStage | null) {
  return useQuery({
    queryKey: ["training", "module", userId, stage],
    queryFn: () => getTrainingModule(userId as number, stage as TrainingStage),
    enabled: userId !== null && stage !== null,
  });
}

export function useSubmitTraining() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: TrainingSubmitRequest) => submitTraining(payload),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["training", "status", variables.user_id] });
    },
  });
}
