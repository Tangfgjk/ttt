import { apiClient } from "@/services/api-client";
import type { QuestionListResponse } from "@/types/question";

export async function getQuestionList() {
  const response = await apiClient.get<QuestionListResponse>("/questions");
  return response.data;
}
