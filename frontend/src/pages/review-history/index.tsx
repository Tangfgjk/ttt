import { EyeOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Empty,
  Input,
  Result,
  Segmented,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { type ChangeEvent, useMemo, useState } from "react";

import { formatBackendDateTime, parseBackendDateTime } from "@/app/date-time";
import { useAuthStore } from "@/app/store/auth-store";
import { QuestionRichText } from "@/components/question-rich-text";
import { getAnnotationStatusColor, getAnnotationStatusLabel } from "@/constants/annotation-status";
import { useReviewTasks } from "@/modules/annotations/hooks";
import type { ReviewTask } from "@/types/annotations";

export function ReviewHistoryPage() {
  const session = useAuthStore((state) => state.session);
  const reviewerId = session?.id ?? null;
  const historyQuery = useReviewTasks(reviewerId, "COMPLETED");
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [keyword, setKeyword] = useState("");
  const [subjectFilter, setSubjectFilter] = useState<string>("all");
  const [timeFilter, setTimeFilter] = useState<"all" | "7d" | "30d">("all");
  const items = historyQuery.data?.items ?? [];
  const subjectOptions = useMemo(
    () => [
      { value: "all", label: "全部学科" },
      ...Array.from(new Set(items.map((item) => item.question.subject.name))).map((subject) => ({
        value: subject,
        label: subject,
      })),
    ],
    [items],
  );
  const filteredItems = useMemo(() => {
    const normalizedKeyword = keyword.trim().toLowerCase();
    return items.filter((item) => {
      if (subjectFilter !== "all" && item.question.subject.name !== subjectFilter) {
        return false;
      }
      if (timeFilter !== "all") {
        const days = timeFilter === "7d" ? 7 : 30;
        const reviewedAt = item.reviewed_at ?? item.created_at;
        const normalizedReviewedAt = parseBackendDateTime(reviewedAt);
        if (normalizedReviewedAt && dayjs(normalizedReviewedAt).isBefore(dayjs().subtract(days, "day"))) {
          return false;
        }
      }
      if (!normalizedKeyword) {
        return true;
      }
      return (
        String(item.question_id).includes(normalizedKeyword) ||
        item.question.subject.name.toLowerCase().includes(normalizedKeyword) ||
        (item.question.content?.stem_text ?? "").toLowerCase().includes(normalizedKeyword) ||
        (item.review_comment ?? "").toLowerCase().includes(normalizedKeyword)
      );
    });
  }, [items, keyword, subjectFilter, timeFilter]);
  const activeItem = useMemo(
    () => items.find((item) => item.id === activeTaskId) ?? null,
    [activeTaskId, items],
  );

  const columns = [
    { title: "复核任务", dataIndex: "id", width: 120 },
    { title: "题目 ID", dataIndex: "question_id", width: 120 },
    {
      title: "学科",
      render: (_: unknown, record: ReviewTask) => record.question.subject.name,
      width: 120,
    },
    {
      title: "最终状态",
      render: (_: unknown, record: ReviewTask) => (
        <Tag color={getAnnotationStatusColor(record.question.annotation_status)}>
          {getAnnotationStatusLabel(record.question.annotation_status)}
        </Tag>
      ),
      width: 140,
    },
    {
      title: "复核完成时间",
      render: (_: unknown, record: ReviewTask) => formatBackendDateTime(record.reviewed_at),
      width: 180,
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: ReviewTask) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => setActiveTaskId(record.id)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card className="hero-panel">
        <Typography.Title level={3} style={{ margin: 0 }}>
          已复核题目
        </Typography.Title>
        <Typography.Text type="secondary">
          查看自己已经完成复核的题目、当时参考的标注结果，以及最终给出的定稿结论。
        </Typography.Text>
      </Card>

      <Card>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Space wrap>
            <Input
              allowClear
              placeholder="搜索题目 ID、题干关键词或复核备注"
              value={keyword}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setKeyword(event.target.value)}
              style={{ width: 280 }}
            />
            <Select
              value={subjectFilter}
              onChange={setSubjectFilter}
              style={{ width: 150 }}
              options={subjectOptions}
            />
            <Segmented
              value={timeFilter}
              onChange={(value: string | number) => setTimeFilter(value as "all" | "7d" | "30d")}
              options={[
                { value: "all", label: "全部时间" },
                { value: "7d", label: "最近 7 天" },
                { value: "30d", label: "最近 30 天" },
              ]}
            />
          </Space>
          <Typography.Text type="secondary">
            当前筛选结果 {filteredItems.length} 条，可快速定位最近复核过的题目和某个学科的历史复核记录。
          </Typography.Text>
        {historyQuery.isLoading ? (
          <Result icon={<Spin size="large" />} title="正在加载已复核题目" />
        ) : filteredItems.length ? (
          <Table<ReviewTask>
            rowKey="id"
            dataSource={filteredItems}
            columns={columns}
            pagination={false}
            scroll={{ x: 920 }}
          />
        ) : (
          <Empty description={items.length ? "当前筛选条件下暂无记录" : "你还没有已完成的复核题目"} />
        )}
        </Space>
      </Card>

      <Drawer
        title={activeItem ? `复核详情 #${activeItem.question_id}` : "复核详情"}
        width={900}
        open={Boolean(activeItem)}
        onClose={() => setActiveTaskId(null)}
        destroyOnClose
      >
        {activeItem ? <ReviewHistoryDetail item={activeItem} /> : null}
      </Drawer>
    </Space>
  );
}

function ReviewHistoryDetail({ item }: { item: ReviewTask }) {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Descriptions
        bordered
        size="small"
        column={2}
        items={[
          { key: "task", label: "复核任务", children: item.id },
          { key: "question", label: "题目 ID", children: item.question_id },
          { key: "subject", label: "学科", children: item.question.subject.name },
          { key: "grade", label: "年级", children: item.question.grade?.grade_name ?? "-" },
          {
            key: "status",
            label: "最终状态",
            children: (
              <Tag color={getAnnotationStatusColor(item.question.annotation_status)}>
                {getAnnotationStatusLabel(item.question.annotation_status)}
              </Tag>
            ),
          },
          { key: "time", label: "完成时间", children: formatBackendDateTime(item.reviewed_at) },
        ]}
      />

      <Card size="small" title="题目内容">
        <QuestionRichText
          html={item.question.content?.stem_html}
          text={item.question.content?.stem_text}
          emptyLabel="暂无题干"
        />
      </Card>

      <Card size="small" title="复核前的标注结果">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          {item.annotations.map((annotation) => (
            <div key={annotation.annotation_id}>
              <Space wrap>
                <Typography.Text strong>{annotation.user_name}</Typography.Text>
                <Tag color="blue">置信度 {annotation.confidence_level ?? "-"}</Tag>
              </Space>
              <Space size={[8, 8]} wrap style={{ marginTop: 8 }}>
                {annotation.competencies.map((competency) => (
                  <Tag key={`${annotation.annotation_id}-${competency.competency_id}`} color={competency.level_value > 0 ? "processing" : "default"}>
                    {competency.competency_name}: L{competency.level_value}
                  </Tag>
                ))}
              </Space>
            </div>
          ))}
        </Space>
      </Card>

      <Card size="small" title="我的复核定稿">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Typography.Text type="secondary">
            {item.review_comment || "未填写额外复核说明。"}
          </Typography.Text>
          <Space size={[8, 8]} wrap>
            {item.aggregate.competencies.map((competency) => (
              <Tag key={competency.competency_id} color={competency.level_value > 0 ? "green" : "default"}>
                {competency.competency_name}: L{competency.level_value}
              </Tag>
            ))}
          </Space>
        </Space>
      </Card>

      <Card size="small" title="操作日志">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          {item.review_logs.map((log) => (
            <div key={log.id}>
              <Space wrap>
                <Tag color={log.actor_role === "reviewer" ? "blue" : log.actor_role === "admin" ? "red" : "default"}>
                  {log.actor_name ?? "系统"}
                </Tag>
                <Typography.Text strong>{log.action_label}</Typography.Text>
                <Typography.Text type="secondary">
                  {formatBackendDateTime(log.created_at)}
                </Typography.Text>
              </Space>
              {log.comment ? (
                <Typography.Paragraph type="secondary" style={{ margin: "6px 0 0" }}>
                  {log.comment}
                </Typography.Paragraph>
              ) : null}
            </div>
          ))}
        </Space>
      </Card>
    </Space>
  );
}
