import { apiClient } from "@/services/api-client";
import type { DictionaryItem, GradeItem } from "@/types/dictionary";

export async function getSubjects() {
  const response = await apiClient.get<DictionaryItem[]>("/dictionaries/subjects");
  return response.data;
}

export async function getGrades() {
  const response = await apiClient.get<GradeItem[]>("/dictionaries/grades");
  return response.data;
}

export async function getQuestionTypes() {
  const response = await apiClient.get<DictionaryItem[]>("/dictionaries/question-types");
  return response.data;
}
