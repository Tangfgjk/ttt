import { apiClient } from "@/services/api-client";
import type {
  ImportBatch,
  ImportBatchDetail,
  ImportRunResponse,
  ImportSourceRecordListResponse,
} from "@/types/imports";

// Imports are processed synchronously on the backend and large files can take
// several minutes to finish, so upload requests should not be canceled by a
// client-side timeout.
const IMPORT_REQUEST_TIMEOUT = 0;

export async function getImportBatches() {
  const response = await apiClient.get<ImportBatch[]>("/imports/batches");
  return response.data;
}

export async function getImportBatchDetail(batchId: number) {
  const response = await apiClient.get<ImportBatchDetail>(`/imports/batches/${batchId}`);
  return response.data;
}

export async function getImportBatchRecords(
  batchId: number,
  params: {
    parse_status?: string;
    page?: number;
    page_size?: number;
  } = {},
) {
  const response = await apiClient.get<ImportSourceRecordListResponse>(
    `/imports/batches/${batchId}/records`,
    {
      params,
    },
  );
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
    timeout: IMPORT_REQUEST_TIMEOUT,
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
    timeout: IMPORT_REQUEST_TIMEOUT,
  });
  return response.data;
}

export async function initializeImportFolderUpload(
  dataSourceCode: string,
  folderName?: string,
  fileCount?: number,
  expectedRecords?: number,
) {
  const formData = new FormData();
  formData.append("data_source_code", dataSourceCode);
  if (folderName) {
    formData.append("folder_name", folderName);
  }
  if (typeof fileCount === "number") {
    formData.append("file_count", String(fileCount));
  }
  if (typeof expectedRecords === "number") {
    formData.append("expected_records", String(expectedRecords));
  }

  const response = await apiClient.post<ImportBatch>("/imports/upload-folder/init", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: IMPORT_REQUEST_TIMEOUT,
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
      timeout: IMPORT_REQUEST_TIMEOUT,
    },
  );
  return response.data;
}
