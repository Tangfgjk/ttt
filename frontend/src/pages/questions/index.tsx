import { Card, Empty, Space, Table, Tag, Typography } from "antd";

import { useQuestionList } from "@/modules/question-bank/hooks";
import type { QuestionListItem } from "@/types/question";

const columns = [
  {
    title: "题目 ID",
    dataIndex: "id",
    width: 100,
  },
  {
    title: "学科",
    render: (_: unknown, record: QuestionListItem) => record.subject.name,
    width: 120,
  },
  {
    title: "年级",
    render: (_: unknown, record: QuestionListItem) => record.grade?.grade_name ?? "-",
    width: 120,
  },
  {
    title: "题型",
    render: (_: unknown, record: QuestionListItem) => record.question_type?.name ?? "-",
    width: 120,
  },
  {
    title: "标注状态",
    dataIndex: "annotation_status",
    width: 120,
    render: (value: string) => <Tag color={value === "PENDING" ? "gold" : "green"}>{value}</Tag>,
  },
  {
    title: "题干摘要",
    render: (_: unknown, record: QuestionListItem) => record.content?.stem_text?.slice(0, 80) ?? "-",
  },
];

export function QuestionsPage() {
  const { data, isLoading } = useQuestionList();

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          统一题池
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          这里是统一 `question_id` 视角的题库入口。后续真实数据归一化落库后，你可以在这里观察题目是否已进入统一题池，以及判重结果是否稳定。
        </Typography.Paragraph>
      </Card>

      <Card>
        {!isLoading && !data?.items.length ? (
          <Empty description="当前统一题池还没有题目数据" />
        ) : (
          <Table<QuestionListItem>
            rowKey="id"
            loading={isLoading}
            columns={columns}
            dataSource={data?.items ?? []}
            pagination={false}
            scroll={{ x: 960 }}
          />
        )}
      </Card>
    </Space>
  );
}
