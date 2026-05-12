import { useQuery } from "@tanstack/react-query";

import {
  getCognitiveLevels,
  getCompetencies,
  getGrades,
  getQuestionTypes,
  getSubjects,
} from "@/services/dictionaries";
import { getQuestionDetail, getQuestionList } from "@/services/questions";
import type { QuestionListParams } from "@/types/question";

export function useQuestionList(params: QuestionListParams) {
  return useQuery({
    queryKey: ["questions", params],
    queryFn: () => getQuestionList(params),
    placeholderData: (previousData) => previousData,
  });
}

export function useQuestionOverview() {
  return useQuery({
    queryKey: ["questions", "overview"],
    queryFn: () => getQuestionList({ page: 1, page_size: 1 }),
  });
}

export function useQuestionDetail(questionId: number | null) {
  return useQuery({
    queryKey: ["questions", "detail", questionId],
    queryFn: () => getQuestionDetail(questionId as number),
    enabled: questionId !== null,
  });
}

export function useSubjects() {
  return useQuery({
    queryKey: ["dictionaries", "subjects"],
    queryFn: getSubjects,
    staleTime: 5 * 60 * 1000,
  });
}

export function useGrades() {
  return useQuery({
    queryKey: ["dictionaries", "grades"],
    queryFn: getGrades,
    staleTime: 5 * 60 * 1000,
  });
}

export function useQuestionTypes() {
  return useQuery({
    queryKey: ["dictionaries", "question-types"],
    queryFn: getQuestionTypes,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCognitiveLevels() {
  return useQuery({
    queryKey: ["dictionaries", "cognitive-levels"],
    queryFn: getCognitiveLevels,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompetencies() {
  return useQuery({
    queryKey: ["dictionaries", "competencies"],
    queryFn: getCompetencies,
    staleTime: 5 * 60 * 1000,
  });
}
