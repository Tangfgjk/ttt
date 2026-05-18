export const runStatusLabelMap: Record<string, string> = {
  PENDING: "待执行",
  RUNNING: "运行中",
  SUCCESS: "成功",
  FAILED: "失败",
};

export const runStatusColorMap: Record<string, string> = {
  PENDING: "default",
  RUNNING: "processing",
  SUCCESS: "green",
  FAILED: "red",
};

export function getRunStatusLabel(status: string) {
  return runStatusLabelMap[status] ?? status;
}

export function getRunStatusColor(status: string) {
  return runStatusColorMap[status] ?? "default";
}
