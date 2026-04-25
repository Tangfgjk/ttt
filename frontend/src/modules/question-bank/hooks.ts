import { useQuery } from "@tanstack/react-query";

import { getQuestionList } from "@/services/questions";

export function useQuestionList() {
  return useQuery({
    queryKey: ["questions"],
    queryFn: getQuestionList,
  });
}
