import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getImportBatchDetail, getImportBatches, uploadImportFile } from "@/services/imports";

export function useImportBatches() {
  return useQuery({
    queryKey: ["import-batches"],
    queryFn: getImportBatches,
  });
}

export function useImportBatchDetail(batchId?: number) {
  return useQuery({
    queryKey: ["import-batches", batchId],
    queryFn: () => getImportBatchDetail(batchId as number),
    enabled: typeof batchId === "number",
  });
}

export function useUploadImport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ dataSourceCode, file }: { dataSourceCode: string; file: File }) =>
      uploadImportFile(dataSourceCode, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["import-batches"] });
    },
  });
}
