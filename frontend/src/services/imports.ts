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
