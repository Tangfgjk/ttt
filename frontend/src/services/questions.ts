import { apiClient } from "@/services/api-client";
import type { QuestionDetail, QuestionListParams, QuestionListResponse } from "@/types/question";

export async function getQuestionList(params: QuestionListParams = {}) {
  const queryParams = {
    ...params,
    question_ids: params.question_ids?.length
      ? params.question_ids.join(",")
      : undefined,
  };
  const response = await apiClient.get<QuestionListResponse>("/questions/", {
    params: queryParams,
  });
  return response.data;
}

export async function getQuestionDetail(questionId: number) {
  const response = await apiClient.get<QuestionDetail>(`/questions/${questionId}`);
  return response.data;
}
