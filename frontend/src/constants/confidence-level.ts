export function getConfidenceLevelLabel(level?: number | null) {
  if (level == null) return "-";
  if (level >= 5) return "高";
  if (level >= 3) return "中";
  return "低";
}
