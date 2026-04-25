import { apiClient } from "@/services/api-client";
import type { ImportBatch } from "@/types/imports";

export async function getImportBatches() {
  const response = await apiClient.get<ImportBatch[]>("/imports/batches");
  return response.data;
}
