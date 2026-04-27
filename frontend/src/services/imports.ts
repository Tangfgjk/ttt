import { apiClient } from "@/services/api-client";
import type { ImportBatch, ImportBatchDetail, ImportRunResponse } from "@/types/imports";

export async function getImportBatches() {
  const response = await apiClient.get<ImportBatch[]>("/imports/batches");
  return response.data;
}

export async function getImportBatchDetail(batchId: number) {
  const response = await apiClient.get<ImportBatchDetail>(`/imports/batches/${batchId}`);
  return response.data;
}

export async function uploadImportFile(dataSourceCode: string, file: File) {
  const formData = new FormData();
  formData.append("data_source_code", dataSourceCode);
  formData.append("file", file);

  const response = await apiClient.post<ImportRunResponse>("/imports/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 60_000,
  });
  return response.data;
}

export async function uploadImportFolder(
  dataSourceCode: string,
  files: File[],
  folderName?: string,
) {
  const formData = new FormData();
  formData.append("data_source_code", dataSourceCode);
  if (folderName) {
    formData.append("folder_name", folderName);
  }
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await apiClient.post<ImportRunResponse>("/imports/upload-folder", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 300_000,
  });
  return response.data;
}

export async function initializeImportFolderUpload(
  dataSourceCode: string,
  folderName?: string,
  fileCount?: number,
) {
  const formData = new FormData();
  formData.append("data_source_code", dataSourceCode);
  if (folderName) {
    formData.append("folder_name", folderName);
  }
  if (typeof fileCount === "number") {
    formData.append("file_count", String(fileCount));
  }

  const response = await apiClient.post<ImportBatch>("/imports/upload-folder/init", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 60_000,
  });
  return response.data;
}

export async function uploadImportBatchChunk(
  batchId: number,
  files: File[],
  finalize: boolean,
) {
  const formData = new FormData();
  formData.append("finalize", finalize ? "true" : "false");
  files.forEach((file) => {
    formData.append("files", file);
  });

  const response = await apiClient.post<ImportRunResponse>(
    `/imports/batches/${batchId}/upload-chunk`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 300_000,
    },
  );
  return response.data;
}
