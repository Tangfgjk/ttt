import { CheckCircleOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Col, List, Row, Space, Statistic, Tag, Typography } from "antd";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/app/store/auth-store";
import { useWorkspaceSummary } from "@/modules/annotations/hooks";

export function WorkspacePage() {
  const navigate = useNavigate();
  const session = useAuthStore((state) => state.session);
  const workspaceSummaryQuery = useWorkspaceSummary(session?.id ?? null);
  const trainingScope = session?.trainingScope ?? "none";
  const needsTraining = session?.role === "annotator" && trainingScope === "none";
  const isReviewer = session?.role === "reviewer";
  const summary = workspaceSummaryQuery.data;

  const myTodoItems = useMemo(
    () =>
      isReviewer
        ? [
            summary?.pending_task_count
              ? {
                  label: `优先处理你当前已领取的 ${summary.pending_task_count} 道待复核题。`,
                  tone: "red",
                  actionLabel: "继续复核",
                  onClick: () => navigate("/review"),
                }
              : {
                  label: "当前没有已领取复核题，可以去复核页一键领取新的待复核题。",
                  tone: "blue",
                  actionLabel: "去领取待复核题",
                  onClick: () => navigate("/review"),
                },
            summary?.completed_today_count
              ? {
                  label: `今天已完成 ${summary.completed_today_count} 道复核，当前节奏不错，可以继续处理新的待复核题。`,
                  tone: "green",
                }
              : {
                  label: "今天还没有完成复核，建议优先处理一条待复核题，尽快建立当日进度。",
                  tone: "gold",
                  actionLabel: "开始复核",
                  onClick: () => navigate("/review"),
                },
            summary?.completed_review_count
              ? {
                  label: `你累计已完成 ${summary.completed_review_count} 道复核，可随时回看自己的定稿记录。`,
                  tone: "purple",
                  actionLabel: "查看已复核题目",
                  onClick: () => navigate("/review-history"),
                }
              : {
                  label: "完成首条复核后，就可以在“已复核题目”里回看自己的定稿结论。",
                  tone: "default",
                },
          ]
        : [
            needsTraining
              ? {
                  label: "先完成培训准入，再进入正式标注；通过后系统会自动开放对应学段题目。",
                  tone: "orange",
                  actionLabel: "前往培训",
                  onClick: () => navigate("/annotator-training"),
                }
              : summary?.pending_task_count
                ? {
                    label: `继续处理你当前已领取的 ${summary.pending_task_count} 道待标注题，优先把手上的题做完。`,
                    tone: "red",
                    actionLabel: "继续标注",
                    onClick: () => navigate("/annotate"),
                  }
                : {
                    label: "当前没有已领取标注题，可以去标注页领取新题并开始新一轮标注。",
                    tone: "blue",
                    actionLabel: "去领取题目",
                    onClick: () => navigate("/annotate"),
                  },
            summary?.completed_today_count
              ? {
                  label: `今天已提交 ${summary.completed_today_count} 道标注，可以继续保持节奏，稳定积累训练样本。`,
                  tone: "green",
                }
              : {
                  label: "今天还没有提交标注，建议先完成一轮核心素养矩阵标注，建立当日进度。",
                  tone: "gold",
                  actionLabel: needsTraining ? "查看培训" : "开始标注",
                  onClick: () => navigate(needsTraining ? "/annotator-training" : "/annotate"),
                },
            summary?.escalated_count
              ? {
                  label: `已有 ${summary.escalated_count} 道你参与的题进入过复核，建议回看历史记录并关注最终反馈。`,
                  tone: "purple",
                  actionLabel: "查看我的标注记录",
                  onClick: () => navigate("/annotation-history"),
                }
              : {
                  label: "当前你参与的题目还没有进入复核，可继续积累稳定标注样本并熟悉素养边界。",
                  tone: "default",
                },
          ],
    [
      isReviewer,
      navigate,
      needsTraining,
      summary?.completed_review_count,
      summary?.completed_today_count,
      summary?.escalated_count,
      summary?.pending_task_count,
    ],
  );

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      {needsTraining ? (
        <Alert
          type="warning"
          showIcon
          icon={<SafetyCertificateOutlined />}
          message="当前账号尚未完成培训准入"
          description={
            <Button type="link" style={{ paddingLeft: 0 }} onClick={() => navigate("/annotator-training")}>
              前往培训页完成初中或高中培训
            </Button>
          }
        />
      ) : null}

      <Card className="hero-panel">
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          我的工作台
        </Typography.Title>
        <Typography.Paragraph>
          这里优先展示“我今天该做什么”。标注员可以继续做题并回看自己的历史标注；复核员可以继续处理待复核题，并查看自己已经完成的复核记录。
        </Typography.Paragraph>
        <Space wrap>
          <Tag color="green">{session?.name}</Tag>
          <Tag color="blue">{isReviewer ? "复核视角" : "标注视角"}</Tag>
          {session?.role === "annotator" ? (
            <Tag icon={<CheckCircleOutlined />} color={needsTraining ? "default" : "success"}>
              {needsTraining ? "未通过培训" : `培训范围：${trainingScope}`}
            </Tag>
          ) : null}
        </Space>
        <Space wrap>
          {session?.role === "annotator" ? (
            <>
              <Button type="primary" onClick={() => navigate(needsTraining ? "/annotator-training" : "/annotate")}>
                {needsTraining ? "前往培训" : "继续标注"}
              </Button>
              <Button onClick={() => navigate("/annotation-history")}>查看我的标注记录</Button>
            </>
          ) : null}
          {isReviewer ? (
            <>
              <Button type="primary" onClick={() => navigate("/review")}>继续复核</Button>
              <Button onClick={() => navigate("/review-history")}>查看已复核题目</Button>
            </>
          ) : null}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title={isReviewer ? "我的待复核题" : "我的待标注题"}
              value={summary?.pending_task_count ?? 0}
              loading={workspaceSummaryQuery.isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="今日已完成"
              value={summary?.completed_today_count ?? 0}
              loading={workspaceSummaryQuery.isLoading}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title={isReviewer ? "已完成复核" : "进入复核的题"}
              value={
                isReviewer
                  ? (summary?.completed_review_count ?? 0)
                  : (summary?.escalated_count ?? 0)
              }
              loading={workspaceSummaryQuery.isLoading}
            />
          </Card>
        </Col>
      </Row>

      <Card title="当前建议动作">
        <List
          dataSource={myTodoItems}
          renderItem={(item: { label: string; tone: string; actionLabel?: string; onClick?: () => void }) => (
            <List.Item>
              <Space style={{ justifyContent: "space-between", width: "100%" }} wrap>
                <Space>
                  <Tag color={item.tone}>建议</Tag>
                  <span>{item.label}</span>
                </Space>
                {item.actionLabel && item.onClick ? (
                  <Button size="small" onClick={item.onClick}>
                    {item.actionLabel}
                  </Button>
                ) : null}
              </Space>
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}
