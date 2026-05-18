import type { AnnotationPoolStatus } from "@/types/annotations";

export const annotationStatusLabelMap: Record<AnnotationPoolStatus, string> = {
  PENDING: "未标注",
  WAITING: "待标注",
  IN_PROGRESS: "标注中",
  REVIEW_PENDING: "待复核",
  COMPLETED: "已完成",
};

export const annotationStatusColorMap: Record<AnnotationPoolStatus, string> = {
  PENDING: "gold",
  WAITING: "blue",
  IN_PROGRESS: "purple",
  REVIEW_PENDING: "orange",
  COMPLETED: "green",
};

export const annotationStatusOptions = [
  { label: "全部状态", value: "" },
  { label: annotationStatusLabelMap.PENDING, value: "PENDING" },
  { label: annotationStatusLabelMap.WAITING, value: "WAITING" },
  { label: annotationStatusLabelMap.IN_PROGRESS, value: "IN_PROGRESS" },
  { label: annotationStatusLabelMap.REVIEW_PENDING, value: "REVIEW_PENDING" },
  { label: annotationStatusLabelMap.COMPLETED, value: "COMPLETED" },
];

const annotationTaskStatusLabelMap: Record<string, string> = {
  IN_PROGRESS: "进行中",
  SUBMITTED: "已提交",
  RECALLED: "已回收",
};

export function getAnnotationStatusLabel(status: string) {
  return annotationStatusLabelMap[status as AnnotationPoolStatus] ?? status;
}

export function getAnnotationStatusColor(status: string) {
  return annotationStatusColorMap[status as AnnotationPoolStatus] ?? "default";
}

export function getAnnotationTaskStatusLabel(status: string) {
  return annotationTaskStatusLabelMap[status] ?? status;
}
