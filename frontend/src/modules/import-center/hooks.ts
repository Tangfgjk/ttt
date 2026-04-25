import { useQuery } from "@tanstack/react-query";

import { getImportBatches } from "@/services/imports";

export function useImportBatches() {
  return useQuery({
    queryKey: ["import-batches"],
    queryFn: getImportBatches,
  });
}
