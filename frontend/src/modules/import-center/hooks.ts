import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getImportBatchDetail,
  getImportBatchRecords,
  getImportBatches,
  initializeImportFolderUpload,
  uploadImportBatchChunk,
  uploadImportFile,
  uploadImportFolder,
} from "@/services/imports";

function isActiveImportStatus(status: string | undefined) {
  return status === "UPLOADING" || status === "QUEUED" || status === "RUNNING";
}

export function useImportBatches() {
  return useQuery({
    queryKey: ["import-batches"],
    queryFn: getImportBatches,
    refetchInterval: (query) =>
      query.state.data?.some((item) => isActiveImportStatus(item.import_status)) ? 2_000 : false,
  });
}

export function useImportBatchDetail(batchId?: number) {
  return useQuery({
    queryKey: ["import-batches", batchId],
    queryFn: () => getImportBatchDetail(batchId as number),
    enabled: typeof batchId === "number",
    refetchInterval: (query) =>
      isActiveImportStatus(query.state.data?.batch.import_status) ? 2_000 : false,
  });
}

export function useImportBatchRecords(
  batchId: number | undefined,
  params: {
    parse_status?: string;
    normalized_question_id?: number;
    page?: number;
    page_size?: number;
  },
) {
  return useQuery({
    queryKey: ["import-batches", batchId, "records", params],
    queryFn: () => getImportBatchRecords(batchId as number, params),
    enabled: typeof batchId === "number",
    placeholderData: (previousData) => previousData,
  });
}

export function useUploadImport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ dataSourceCode, file }: { dataSourceCode: string; file: File }) =>
      uploadImportFile(dataSourceCode, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      void queryClient.invalidateQueries({ queryKey: ["questions"] });
      void queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}

export function useUploadImportFolder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      dataSourceCode,
      files,
      folderName,
    }: {
      dataSourceCode: string;
      files: File[];
      folderName?: string;
    }) => uploadImportFolder(dataSourceCode, files, folderName),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      void queryClient.invalidateQueries({ queryKey: ["questions"] });
      void queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}

export function useInitializeImportFolderUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      dataSourceCode,
      folderName,
      fileCount,
      expectedRecords,
    }: {
      dataSourceCode: string;
      folderName?: string;
      fileCount?: number;
      expectedRecords?: number;
    }) => initializeImportFolderUpload(dataSourceCode, folderName, fileCount, expectedRecords),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      void queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}

export function useUploadImportBatchChunk() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      batchId,
      files,
      finalize,
    }: {
      batchId: number;
      files: File[];
      finalize: boolean;
    }) => uploadImportBatchChunk(batchId, files, finalize),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      void queryClient.invalidateQueries({ queryKey: ["questions"] });
      void queryClient.invalidateQueries({ queryKey: ["active-learning"] });
    },
  });
}
