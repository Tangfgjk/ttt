export const importBatchStatusLabelMap: Record<string, string> = {
  UPLOADING: "上传中",
  QUEUED: "排队中",
  PENDING: "待执行",
  RUNNING: "处理中",
  SUCCESS: "成功",
  PARTIAL_SUCCESS: "部分成功",
  FAILED: "失败",
};

export const importBatchStatusColorMap: Record<string, string> = {
  UPLOADING: "blue",
  QUEUED: "gold",
  PENDING: "default",
  RUNNING: "processing",
  SUCCESS: "green",
  PARTIAL_SUCCESS: "gold",
  FAILED: "red",
};

export const importParseStatusLabelMap: Record<string, string> = {
  CREATED_NEW_QUESTION: "新建题目",
  MATCHED_BY_EXTERNAL_ID: "按外部 ID 匹配",
  MATCHED_BY_CONTENT_HASH: "按内容指纹匹配",
  MATCHED_BY_REVIEW: "经复核后匹配",
  CREATED_BY_REVIEW: "经复核后新建",
  PENDING_REVIEW: "待复核确认",
  FAILED: "处理失败",
  RAW_IMPORTED: "原始导入",
};

export const importParseStatusColorMap: Record<string, string> = {
  CREATED_NEW_QUESTION: "green",
  MATCHED_BY_EXTERNAL_ID: "blue",
  MATCHED_BY_CONTENT_HASH: "cyan",
  MATCHED_BY_REVIEW: "purple",
  CREATED_BY_REVIEW: "lime",
  PENDING_REVIEW: "gold",
  FAILED: "red",
  RAW_IMPORTED: "default",
};

export function getImportBatchStatusLabel(status: string) {
  return importBatchStatusLabelMap[status] ?? status;
}

export function getImportBatchStatusColor(status: string) {
  return importBatchStatusColorMap[status] ?? "default";
}

export function getImportParseStatusLabel(status: string) {
  return importParseStatusLabelMap[status] ?? status;
}

export function getImportParseStatusColor(status: string) {
  return importParseStatusColorMap[status] ?? "default";
}
