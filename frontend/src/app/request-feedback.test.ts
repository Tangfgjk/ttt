import { describe, expect, it } from "vitest";

import { getRequestFeedback } from "./request-feedback";


describe("getRequestFeedback", () => {
  it("uses a warning for an unavailable machine-learning runtime", () => {
    const feedback = getRequestFeedback(
      {
        response: {
          status: 503,
          data: { detail: "当前服务器未安装机器学习运行环境。" },
        },
      },
      "模型训练失败",
    );

    expect(feedback).toEqual({
      level: "warning",
      content: "当前服务器未安装机器学习运行环境。",
    });
  });

  it("uses an error for ordinary request failures", () => {
    const feedback = getRequestFeedback(new Error("network down"), "CoreSet 选题失败");

    expect(feedback).toEqual({
      level: "error",
      content: "CoreSet 选题失败：network down",
    });
  });
});
