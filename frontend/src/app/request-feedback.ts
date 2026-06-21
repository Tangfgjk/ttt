export type RequestFeedback = {
  level: "warning" | "error";
  content: string;
};


type RequestErrorLike = {
  code?: string;
  message?: string;
  response?: {
    status?: number;
    data?: { detail?: string };
  };
};


export function getRequestFeedback(error: unknown, fallback: string): RequestFeedback {
  const requestError = error as RequestErrorLike;
  const detail = requestError.response?.data?.detail;
  if (requestError.response?.status === 503) {
    return {
      level: "warning",
      content: detail || "当前服务器未安装机器学习运行环境，请在本地环境使用该功能。",
    };
  }
  if (detail) {
    return { level: "error", content: detail };
  }
  if (requestError.code === "ECONNABORTED") {
    return { level: "error", content: `${fallback}：请求超时，请稍后重试。` };
  }
  if (requestError.message) {
    return { level: "error", content: `${fallback}：${requestError.message}` };
  }
  return { level: "error", content: fallback };
}
