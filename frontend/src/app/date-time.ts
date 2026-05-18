const HAS_TIMEZONE_SUFFIX = /(?:Z|[+-]\d{2}:?\d{2})$/;

export function parseBackendDateTime(value?: string | null) {
  if (!value) return null;
  const normalized = HAS_TIMEZONE_SUFFIX.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

export function formatBackendDateTime(value?: string | null) {
  if (!value) return "-";
  const date = parseBackendDateTime(value);
  if (!date) return value.replace("T", " ").slice(0, 19);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}
