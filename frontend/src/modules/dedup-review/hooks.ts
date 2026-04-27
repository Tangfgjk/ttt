import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveDuplicateCandidate,
  getDuplicateReviewCandidates,
  rejectDuplicateCandidate,
} from "@/services/dedup-review";

export function useDuplicateReviewCandidates(reviewStatus = "PENDING") {
  return useQuery({
    queryKey: ["dedup-review-candidates", reviewStatus],
    queryFn: () => getDuplicateReviewCandidates(reviewStatus),
  });
}

export function useApproveDuplicateCandidate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      candidateId,
      reviewedByUserId,
    }: {
      candidateId: number;
      reviewedByUserId: number;
    }) => approveDuplicateCandidate(candidateId, reviewedByUserId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dedup-review-candidates"] });
      await queryClient.invalidateQueries({ queryKey: ["import-batches"] });
    },
  });
}

export function useRejectDuplicateCandidate() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      candidateId,
      reviewedByUserId,
    }: {
      candidateId: number;
      reviewedByUserId: number;
    }) => rejectDuplicateCandidate(candidateId, reviewedByUserId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dedup-review-candidates"] });
      await queryClient.invalidateQueries({ queryKey: ["import-batches"] });
    },
  });
}
