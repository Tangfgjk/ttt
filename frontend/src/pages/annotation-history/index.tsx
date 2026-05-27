import { CheckCircleOutlined, ClockCircleOutlined, EyeOutlined, SyncOutlined } from "@ant-design/icons";
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
import { type ChangeEvent, useMemo, useState } from "react";

import { formatBackendDateTime } from "@/app/date-time";
import { useAuthStore } from "@/app/store/auth-store";
import { QuestionRichText } from "@/components/question-rich-text";
import { getAnnotationStatusColor, getAnnotationStatusLabel } from "@/constants/annotation-status";
import { getConfidenceLevelLabel } from "@/constants/confidence-level";
import { useAnnotatorHistory } from "@/modules/annotations/hooks";
import type { AnnotatorHistoryItem } from "@/types/annotations";

export function AnnotationHistoryPage() {
  const session = useAuthStore((state) => state.session);
  const annotatorId = session?.id ?? null;
  const [activeAnnotationId, setActiveAnnotationId] = useState<number | null>(null);
  const [keyword, setKeyword] = useState("");
  const [reviewFilter, setReviewFilter] = useState<"all" | AnnotatorHistoryItem["review_state"]>("all");
  const [adoptionFilter, setAdoptionFilter] = useState<"all" | AnnotatorHistoryItem["adoption_status"]>("all");
  const [timeFilter, setTimeFilter] = useState<"all" | "7d" | "30d">("all");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const historyQuery = useAnnotatorHistory(annotatorId, {
    page,
    page_size: pageSize,
    keyword: keyword.trim() || undefined,
    review_state: reviewFilter === "all" ? undefined : reviewFilter,
    adoption_status: adoptionFilter === "all" ? undefined : adoptionFilter,
    time_range: timeFilter === "all" ? undefined : timeFilter,
  });

  const items = historyQuery.data?.items ?? [];
  const activeItem = useMemo(
    () => items.find((item) => item.annotation_id === activeAnnotationId) ?? null,
    [activeAnnotationId, items],
  );

  const columns = [
    {
      title: "题目 ID",
      dataIndex: "question_id",
      width: 120,
    },
    {
      title: "学科",
      render: (_: unknown, record: AnnotatorHistoryItem) => record.question.subject.name,
      width: 120,
    },
    {
      title: "当前状态",
      render: (_: unknown, record: AnnotatorHistoryItem) => (
        <Tag color={getAnnotationStatusColor(record.question_status)}>
          {getAnnotationStatusLabel(record.question_status)}
        </Tag>
      ),
      width: 140,
    },
    {
      title: "是否复核",
      render: (_: unknown, record: AnnotatorHistoryItem) => reviewStateTag(record.review_state),
      width: 140,
    },
    {
      title: "是否通过",
      render: (_: unknown, record: AnnotatorHistoryItem) => adoptionStatusTag(record.adoption_status),
      width: 160,
    },
    {
      title: "提交时间",
      render: (_: unknown, record: AnnotatorHistoryItem) => formatBackendDateTime(record.submitted_at),
      width: 180,
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      render: (_: unknown, record: AnnotatorHistoryItem) => (
        <Button type="link" icon={<EyeOutlined />} onClick={() => setActiveAnnotationId(record.annotation_id)}>
          查看详情
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card className="hero-panel">
        <Typography.Title level={3} style={{ margin: 0 }}>
          我的标注记录
        </Typography.Title>
        <Typography.Text type="secondary">
          查看自己已经提交过的题目、当时的标注结果，以及这道题最终是否进入复核、是否与最终结论一致。
        </Typography.Text>
      </Card>

      <Card>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Space wrap>
            <Input
              allowClear
              placeholder="搜索题目 ID、学科或题干关键词"
              value={keyword}
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                setKeyword(event.target.value);
                setPage(1);
              }}
              style={{ width: 260 }}
            />
            <Select
              value={reviewFilter}
              onChange={(value: "all" | AnnotatorHistoryItem["review_state"]) => {
                setReviewFilter(value);
                setPage(1);
              }}
              style={{ width: 150 }}
              options={[
                { value: "all", label: "全部复核状态" },
                { value: "NOT_REQUIRED", label: "无需复核" },
                { value: "PENDING", label: "待复核" },
                { value: "COMPLETED", label: "已复核" },
              ]}
            />
            <Select
              value={adoptionFilter}
              onChange={(value: "all" | AnnotatorHistoryItem["adoption_status"]) => {
                setAdoptionFilter(value);
                setPage(1);
              }}
              style={{ width: 150 }}
              options={[
                { value: "all", label: "全部采纳结果" },
                { value: "PASSED", label: "已采纳" },
                { value: "OVERRIDDEN", label: "已调整" },
                { value: "PENDING", label: "待定" },
              ]}
            />
            <Segmented
              value={timeFilter}
              onChange={(value: string | number) => {
                setTimeFilter(value as "all" | "7d" | "30d");
                setPage(1);
              }}
              options={[
                { value: "all", label: "全部时间" },
                { value: "7d", label: "最近 7 天" },
                { value: "30d", label: "最近 30 天" },
              ]}
            />
          </Space>
          <Typography.Text type="secondary">
            当前筛选结果 {historyQuery.data?.meta.total ?? 0} 条，默认每页 20 条，可翻页查看全部记录。
          </Typography.Text>
        {historyQuery.isLoading ? (
          <Result icon={<Spin size="large" />} title="正在加载我的标注记录" />
        ) : items.length ? (
          <Table<AnnotatorHistoryItem>
            rowKey="annotation_id"
            dataSource={items}
            columns={columns}
            pagination={{
              current: page,
              pageSize,
              total: historyQuery.data?.meta.total ?? 0,
              showSizeChanger: true,
              pageSizeOptions: [20, 50, 100],
              onChange: (nextPage: number, nextPageSize: number) => {
                setPage(nextPage);
                setPageSize(nextPageSize);
              },
            }}
            scroll={{ x: 980 }}
          />
        ) : (
          <Empty description={items.length ? "当前筛选条件下暂无记录" : "你还没有已提交的标注记录"} />
        )}
        </Space>
      </Card>

      <Drawer
        title={activeItem ? `标注详情 #${activeItem.question_id}` : "标注详情"}
        width={860}
        open={Boolean(activeItem)}
        onClose={() => setActiveAnnotationId(null)}
        destroyOnClose
      >
        {activeItem ? <AnnotationHistoryDetail item={activeItem} /> : null}
      </Drawer>
    </Space>
  );
}

function AnnotationHistoryDetail({ item }: { item: AnnotatorHistoryItem }) {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Descriptions
        bordered
        size="small"
        column={2}
        items={[
          { key: "question", label: "题目 ID", children: item.question_id },
          { key: "subject", label: "学科", children: item.question.subject.name },
          { key: "grade", label: "年级", children: item.question.grade?.grade_name ?? "-" },
          {
            key: "status",
            label: "当前状态",
            children: (
              <Tag color={getAnnotationStatusColor(item.question_status)}>
                {getAnnotationStatusLabel(item.question_status)}
              </Tag>
            ),
          },
          { key: "review", label: "复核状态", children: reviewStateTag(item.review_state) },
          { key: "adoption", label: "最终采纳", children: adoptionStatusTag(item.adoption_status) },
        ]}
      />

      <Card size="small" title="题目内容">
        <QuestionRichText
          html={item.question.content?.stem_html}
          text={item.question.content?.stem_text}
          emptyLabel="暂无题干"
        />
      </Card>

      <Card size="small" title="我的标注结果">
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Space wrap>
            <Typography.Text type="secondary">
              提交于 {formatBackendDateTime(item.submitted_at)}
            </Typography.Text>
          </Space>
          <Space size={[8, 8]} wrap>
            {item.annotation.competencies.map((competency) => (
              <Tag key={competency.competency_id} color={competency.level_value > 0 ? "processing" : "default"}>
                {competency.competency_name}: L{competency.level_value} · 信心等级
                {getConfidenceLevelLabel(competency.confidence_level ?? 5)}
              </Tag>
            ))}
          </Space>
        </Space>
      </Card>

      <Card size="small" title="最终结论">
        {item.final_aggregate ? (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Typography.Text type="secondary">
              最终一致率 {item.final_aggregate.agreement_score ?? "-"}，
              {item.review_state === "COMPLETED" ? "由复核员定稿" : "由系统自动收敛"}。
            </Typography.Text>
            <Space size={[8, 8]} wrap>
              {item.final_aggregate.competencies.map((competency) => (
                <Tag key={competency.competency_id} color={competency.level_value > 0 ? "green" : "default"}>
                  {competency.competency_name}: L{competency.level_value}
                </Tag>
              ))}
            </Space>
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="该题还没有最终结论" />
        )}
      </Card>

      <Card size="small" title="流转日志">
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

function reviewStateTag(value: AnnotatorHistoryItem["review_state"]) {
  if (value === "COMPLETED") {
    return <Tag color="green" icon={<CheckCircleOutlined />}>已复核</Tag>;
  }
  if (value === "PENDING") {
    return <Tag color="orange" icon={<SyncOutlined />}>待复核</Tag>;
  }
  return <Tag icon={<ClockCircleOutlined />}>无需复核</Tag>;
}

function adoptionStatusTag(value: AnnotatorHistoryItem["adoption_status"]) {
  if (value === "PASSED") {
    return <Tag color="green">已采纳</Tag>;
  }
  if (value === "OVERRIDDEN") {
    return <Tag color="red">已调整</Tag>;
  }
  return <Tag color="default">待定</Tag>;
}
