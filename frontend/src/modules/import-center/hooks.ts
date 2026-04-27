import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getImportBatchDetail,
  getImportBatches,
  initializeImportFolderUpload,
  uploadImportBatchChunk,
  uploadImportFile,
  uploadImportFolder,
} from "@/services/imports";

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
      void queryClient.invalidateQueries({ queryKey: ["questions"] });
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
    }: {
      dataSourceCode: string;
      folderName?: string;
      fileCount?: number;
    }) => initializeImportFolderUpload(dataSourceCode, folderName, fileCount),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["import-batches"] });
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
    },
  });
}
