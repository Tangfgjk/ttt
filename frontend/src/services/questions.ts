import { apiClient } from "@/services/api-client";
import type { QuestionDetail, QuestionListParams, QuestionListResponse } from "@/types/question";

export async function getQuestionList(params: QuestionListParams = {}) {
  const response = await apiClient.get<QuestionListResponse>("/questions/", { params });
  return response.data;
}

export async function getQuestionDetail(questionId: number) {
  const response = await apiClient.get<QuestionDetail>(`/questions/${questionId}`);
  return response.data;
}
