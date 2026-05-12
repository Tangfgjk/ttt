import { apiClient } from "@/services/api-client";
import type {
  BulkApproveDuplicateRequest,
  BulkApproveDuplicateResponse,
  DuplicateReviewItem,
  ReviewDecisionResponse,
} from "@/types/dedup-review";

export async function getDuplicateReviewCandidates(reviewStatus = "PENDING") {
  const response = await apiClient.get<DuplicateReviewItem[]>("/dedup-review/candidates", {
    params: { review_status: reviewStatus },
  });
  return response.data;
}

export async function approveDuplicateCandidate(candidateId: number, reviewedByUserId: number) {
  const response = await apiClient.post<ReviewDecisionResponse>(
    `/dedup-review/candidates/${candidateId}/approve`,
    {
      reviewed_by_user_id: reviewedByUserId,
    },
  );
  return response.data;
}

export async function rejectDuplicateCandidate(candidateId: number, reviewedByUserId: number) {
  const response = await apiClient.post<ReviewDecisionResponse>(
    `/dedup-review/candidates/${candidateId}/reject`,
    {
      reviewed_by_user_id: reviewedByUserId,
    },
  );
  return response.data;
}

export async function bulkApproveDuplicateCandidates(payload: BulkApproveDuplicateRequest) {
  const response = await apiClient.post<BulkApproveDuplicateResponse>(
    "/dedup-review/candidates/bulk-approve",
    payload,
  );
  return response.data;
}
