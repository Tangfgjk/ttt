import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Form,
  Input,
  Result,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { usePageHashScroll } from "@/app/use-page-hash-scroll";
import { useAuthStore } from "@/app/store/auth-store";
import { QuestionRichText } from "@/components/question-rich-text";
import {
  useAdminQuestionReview,
} from "@/modules/annotations/hooks";
import {
  useGrades,
  useQuestionDetail,
  useQuestionList,
  useQuestionOverview,
  useQuestionTypes,
  useSubjects,
} from "@/modules/question-bank/hooks";
import type { AdminQuestionReview } from "@/types/annotations";
import type { QuestionDetail, QuestionListItem, QuestionListParams } from "@/types/question";

const DEFAULT_PAGE_SIZE = 20;

const annotationStatusOptions = [
  { label: "全部状态", value: "" },
  { label: "未标注池", value: "PENDING" },
  { label: "待标注池", value: "WAITING" },
  { label: "领取锁定池", value: "IN_PROGRESS" },
  { label: "待复核池", value: "REVIEW_PENDING" },
  { label: "已标注池", value: "COMPLETED" },
];

const detailViewModeOptions = [
  { label: "渲染视图", value: "rendered" },
  { label: "原始文本", value: "raw" },
] as const;

type DetailViewMode = (typeof detailViewModeOptions)[number]["value"];

const statusColorMap: Record<string, string> = {
  PENDING: "gold",
  WAITING: "blue",
  IN_PROGRESS: "purple",
  REVIEW_PENDING: "orange",
  COMPLETED: "green",
};

function RawTextBlock({
  value,
  emptyLabel = "暂无内容",
}: {
  value?: string | null;
  emptyLabel?: string;
}) {
  if (!value) {
    return <Typography.Text type="secondary">{emptyLabel}</Typography.Text>;
  }
  return <pre className="question-raw-block">{value}</pre>;
}

function QuestionDetailDrawerContent({
  detail,
  viewMode,
  onViewModeChange,
  adminReview,
}: {
  detail: QuestionDetail;
  viewMode: DetailViewMode;
  onViewModeChange: (value: DetailViewMode) => void;
  adminReview?: AdminQuestionReview | null;
}) {
  const isRawMode = viewMode === "raw";

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Space style={{ justifyContent: "space-between", width: "100%" }} wrap>
        <Typography.Title level={5} style={{ margin: 0 }}>
          题目详情
        </Typography.Title>
        <Segmented
          options={detailViewModeOptions.map((item) => ({ label: item.label, value: item.value }))}
          value={viewMode}
          onChange={(value: string | number) => onViewModeChange(value as DetailViewMode)}
        />
      </Space>

      <Descriptions
        title="基础信息"
        bordered
        size="small"
        column={2}
        items={[
          { key: "id", label: "题目 ID", children: detail.id },
          { key: "subject", label: "学科", children: detail.subject.name },
          { key: "grade", label: "年级", children: detail.grade?.grade_name ?? "-" },
          { key: "type", label: "题型", children: detail.question_type?.name ?? "-" },
          {
            key: "annotation_status",
            label: "标注状态",
            children: <Tag color={statusColorMap[detail.annotation_status] ?? "default"}>{detail.annotation_status}</Tag>,
          },
          { key: "source_status", label: "来源状态", children: detail.source_status },
          { key: "difficulty", label: "难度", children: detail.difficulty_level ?? "-" },
          { key: "blank_count", label: "填空数量", children: detail.blank_count },
          { key: "annotation_count", label: "已标注人数", children: detail.annotation_count },
          { key: "required_annotations", label: "要求标注人数", children: detail.required_annotations },
        ]}
      />

      <Card size="small" title="完整题干">
        {isRawMode ? (
          <RawTextBlock value={detail.content?.stem_text} emptyLabel="暂无题干" />
        ) : (
          <QuestionRichText
            html={detail.content?.stem_html}
            text={detail.content?.stem_text}
            emptyLabel="暂无题干"
          />
        )}
      </Card>

      {isRawMode && detail.content?.stem_html ? (
        <Card size="small" title="原始 HTML">
          <RawTextBlock value={detail.content.stem_html} emptyLabel="暂无 HTML 内容" />
        </Card>
      ) : null}

      <Card size="small" title="答案">
        {isRawMode ? <RawTextBlock value={detail.content?.answer_text} /> : <QuestionRichText text={detail.content?.answer_text} />}
      </Card>

      <Card size="small" title="解析">
        {isRawMode ? (
          <RawTextBlock value={detail.content?.solution_text} />
        ) : (
          <QuestionRichText text={detail.content?.solution_text} />
        )}
      </Card>

      <Card size="small" title="知识点">
        {detail.knowledge_points.length ? (
          <Space size={[8, 8]} wrap>
            {detail.knowledge_points.map((item) => (
              <Tag key={item.id} color={item.is_core ? "processing" : "default"}>
                {item.knowledge_point_name}
              </Tag>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无知识点信息" />
        )}
      </Card>

      <Card size="small" title="目录信息">
        {detail.catalogs.length ? (
          <Space direction="vertical" size={8} style={{ width: "100%" }}>
            {detail.catalogs.map((item) => (
              <Typography.Text key={item.id}>
                {item.catalog_name}
                {item.school_code ? `（school_code: ${item.school_code}）` : ""}
              </Typography.Text>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无目录信息" />
        )}
      </Card>

      <Card size="small" title="外部来源映射">
        {detail.external_refs.length ? (
          <Space direction="vertical" size={10} style={{ width: "100%" }}>
            {detail.external_refs.map((item) => (
              <div key={item.id}>
                <Typography.Text strong>{item.data_source_name}</Typography.Text>
                <Divider type="vertical" />
                <Typography.Text code>{item.external_question_id}</Typography.Text>
                {item.is_primary ? (
                  <>
                    <Divider type="vertical" />
                    <Tag color="green">主映射</Tag>
                  </>
                ) : null}
              </div>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无来源映射" />
        )}
      </Card>

      {adminReview ? (
        <Card size="small" title="多人标注审阅">
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                { key: "submitted", label: "已提交标注", children: adminReview.submitted_annotation_count },
                { key: "active", label: "并行处理中", children: adminReview.active_annotation_count },
                { key: "required", label: "要求人数", children: adminReview.required_annotations },
                { key: "remaining", label: "剩余补标", children: adminReview.remaining_annotation_count },
                {
                  key: "consensus",
                  label: "一致性状态",
                  children: <Tag color={consensusColor(adminReview.consensus.consensus_status)}>{adminReview.consensus.consensus_status}</Tag>,
                },
                {
                  key: "score",
                  label: "整体一致率",
                  children: adminReview.consensus.agreement_score?.toFixed(2) ?? "-",
                },
              ]}
            />

            <Card size="small" title="标注明细">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                {adminReview.annotations.map((annotation) => (
                  <div key={annotation.annotation_id}>
                    <Space wrap>
                      <Typography.Text strong>{annotation.user_name}</Typography.Text>
                      <Tag>{annotation.task_status ?? "-"}</Tag>
                      <Tag color="blue">置信度 {annotation.confidence_level ?? "-"}</Tag>
                    </Space>
                    <Space size={[8, 8]} wrap style={{ marginTop: 8 }}>
                      {annotation.competencies.map((item) => (
                        <Tag key={`${annotation.annotation_id}-${item.competency_id}`} color={item.level_value > 0 ? "processing" : "default"}>
                          {item.competency_name}: L{item.level_value}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                ))}
              </Space>
            </Card>

            <Card size="small" title="一致性分析">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                {adminReview.consensus.dimensions.map((dimension) => (
                  <div key={`${dimension.dimension_type}-${dimension.dimension_key}`}>
                    <Space wrap>
                      <Typography.Text strong>{dimension.dimension_label}</Typography.Text>
                      <Tag color={consensusColor(dimension.consensus_status)}>{dimension.consensus_status}</Tag>
                      <Typography.Text type="secondary">
                        推荐值：L{dimension.recommended_level_value ?? "-"}，一致率 {dimension.agreement_score.toFixed(2)}
                      </Typography.Text>
                    </Space>
                    <Typography.Paragraph type="secondary" style={{ margin: "6px 0 0" }}>
                      {dimension.vote_summary
                        .map((vote) => `L${vote.level_value ?? "-"}：${vote.vote_count}票（${vote.annotator_names.join("、")}）`)
                        .join("；")}
                    </Typography.Paragraph>
                  </div>
                ))}
              </Space>
            </Card>

            <Card size="small" title="复核流转摘要">
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Typography.Text>
                  争议题会自动进入复核员队列，由复核员处理所有未达成一致的素养维度。
                </Typography.Text>
                <Typography.Text type="secondary">
                  管理员在这里主要查看三位标注员与复核员的操作链路，不再负责手动打回或补票分配。
                </Typography.Text>
                <Space wrap>
                  <Tag color="orange">待处理复核任务 {adminReview.open_review_task_count}</Tag>
                  <Tag color="blue">未解决分歧维度 {adminReview.consensus.unresolved_dimension_count}</Tag>
                </Space>
              </Space>
            </Card>

            <Card size="small" title="审核日志与操作历史">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                {adminReview.review_logs.map((log) => (
                  <div key={log.id}>
                    <Space wrap>
                      <Tag color={log.actor_role === "admin" ? "red" : log.actor_role === "reviewer" ? "blue" : "default"}>
                        {log.actor_name ?? "系统"}
                      </Tag>
                      <Typography.Text strong>{log.action_label}</Typography.Text>
                      <Typography.Text type="secondary">
                        {log.created_at.replace("T", " ").slice(0, 19)}
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
        </Card>
      ) : null}
    </Space>
  );
}

export function QuestionsPage() {
  usePageHashScroll();

  const session = useAuthStore((state) => state.session);
  const isAdmin = session?.role === "admin";
  const [searchParams, setSearchParams] = useSearchParams();
  const [form] = Form.useForm();
  const [filters, setFilters] = useState<QuestionListParams>({
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
  });
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailViewMode, setDetailViewMode] = useState<DetailViewMode>("rendered");

  const questionListQuery = useQuestionList(filters);
  const overviewQuery = useQuestionOverview();
  const subjectsQuery = useSubjects();
  const gradesQuery = useGrades();
  const questionTypesQuery = useQuestionTypes();
  const questionDetailQuery = useQuestionDetail(activeQuestionId);
  const adminReviewQuery = useAdminQuestionReview(
    isAdmin ? activeQuestionId : null,
    isAdmin ? (session?.id ?? null) : null,
  );

  const items = questionListQuery.data?.items ?? [];
  const pageMeta = questionListQuery.data?.meta;
  const overallTotal = overviewQuery.data?.meta.total ?? 0;
  const filteredTotal = pageMeta?.total ?? 0;
  const currentPage = pageMeta?.page ?? filters.page ?? 1;
  const pageSize = pageMeta?.page_size ?? filters.page_size ?? DEFAULT_PAGE_SIZE;
  const totalPages = Math.max(1, Math.ceil(filteredTotal / pageSize));

  useEffect(() => {
    const questionIdParam = searchParams.get("question_id");
    const annotationStatusParam = searchParams.get("annotation_status") ?? undefined;
    const questionIdsParam = searchParams.get("question_ids");
    const questionIds = questionIdsParam
      ?.split(",")
      .map((item) => Number(item.trim()))
      .filter((item) => Number.isInteger(item) && item > 0);

    if (annotationStatusParam) {
      form.setFieldValue("annotation_status", annotationStatusParam);
    }

    setFilters((prev) => ({
      ...prev,
      page: 1,
      annotation_status: annotationStatusParam,
      question_ids: questionIds?.length ? questionIds : undefined,
    }));

    if (!questionIdParam) return;
    const questionId = Number(questionIdParam);
    if (!Number.isInteger(questionId) || questionId <= 0) return;
    setActiveQuestionId(questionId);
    setDrawerOpen(true);
  }, [form, searchParams]);

  const handleSearch = (values: {
    keyword?: string;
    subject_id?: number;
    grade_id?: number;
    question_type_id?: number;
    annotation_status?: string;
  }) => {
    const nextAnnotationStatus = values.annotation_status || undefined;
    setSearchParams((params) => {
      if (nextAnnotationStatus) params.set("annotation_status", nextAnnotationStatus);
      else params.delete("annotation_status");
      return params;
    });
    setFilters({
      page: 1,
      page_size: pageSize,
      keyword: values.keyword?.trim() || undefined,
      subject_id: values.subject_id || undefined,
      grade_id: values.grade_id || undefined,
      question_type_id: values.question_type_id || undefined,
      annotation_status: nextAnnotationStatus,
      question_ids: filters.question_ids,
    });
  };

  const handleReset = () => {
    form.resetFields();
    setSearchParams((params) => {
      params.delete("annotation_status");
      params.delete("question_id");
      return params;
    });
    setFilters({
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
    });
  };

  const openDetailDrawer = (questionId: number) => {
    setActiveQuestionId(questionId);
    setDrawerOpen(true);
  };

  const columns = [
    { title: "题目 ID", dataIndex: "id", width: 110 },
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
      width: 180,
    },
    {
      title: "标注状态",
      dataIndex: "annotation_status",
      width: 150,
      render: (value: string) => <Tag color={statusColorMap[value] ?? "default"}>{value}</Tag>,
    },
    {
      title: "题干摘要",
      render: (_: unknown, record: QuestionListItem) => (
        <QuestionRichText
          html={record.content?.stem_html}
          text={record.content?.stem_text}
          emptyLabel="-"
          className="question-rich-text--summary"
        />
      ),
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      fixed: "right" as const,
      render: (_: unknown, record: QuestionListItem) => (
        <Button type="link" onClick={() => openDetailDrawer(record.id)}>
          查看详情
        </Button>
      ),
    },
  ];

  const detailLoading = questionDetailQuery.isLoading;
  const detail = questionDetailQuery.data;
  const adminReview = adminReviewQuery.data;

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card id="questions-overview" className="hero-panel page-section-anchor">
        <Space direction="vertical" size={4}>
          <Typography.Title level={3} style={{ margin: 0 }}>
            统一题池
          </Typography.Title>
          <Typography.Text type="secondary">
            统一查看题池中的题目，可按标注状态、学科、年级和题型筛选，并进入详情抽屉查看完整题目内容。
          </Typography.Text>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="题池总量" value={overallTotal} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="当前筛选结果" value={filteredTotal} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="总页数" value={totalPages} />
          </Card>
        </Col>
      </Row>

      <Card id="questions-filters" className="page-section-anchor">
        {filters.question_ids?.length ? (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={`当前正在查看指定题目集合，共 ${filters.question_ids.length} 题`}
            description="这个筛选通常来自 CoreSet / 选题批次查看。你仍然可以叠加学科、年级和标注状态筛选。"
          />
        ) : null}
        <Form form={form} layout="vertical" onFinish={handleSearch}>
          <Row gutter={[16, 8]}>
            <Col xs={24} sm={12} lg={8}>
              <Form.Item label="关键词" name="keyword">
                <Input prefix={<SearchOutlined />} placeholder="搜索题干关键词" allowClear />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="学科" name="subject_id">
                <Select
                  allowClear
                  options={(subjectsQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
                  placeholder="全部学科"
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="年级" name="grade_id">
                <Select
                  allowClear
                  options={(gradesQuery.data ?? []).map((item) => ({ value: item.id, label: item.grade_name }))}
                  placeholder="全部年级"
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="题型" name="question_type_id">
                <Select
                  allowClear
                  options={(questionTypesQuery.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
                  placeholder="全部题型"
                />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12} lg={4}>
              <Form.Item label="标注状态" name="annotation_status">
                <Select allowClear options={annotationStatusOptions} placeholder="全部状态" />
              </Form.Item>
            </Col>
          </Row>

          <Space wrap>
            <Button type="primary" htmlType="submit">
              应用筛选
            </Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>
              重置
            </Button>
          </Space>
        </Form>
      </Card>

      <Card id="questions-list" className="page-section-anchor">
        {questionListQuery.isLoading ? (
          <Result icon={<Spin size="large" />} title="正在加载题池数据" />
        ) : (
          <Table<QuestionListItem>
            rowKey="id"
            dataSource={items}
            columns={columns}
            scroll={{ x: 1200 }}
            pagination={{
              current: currentPage,
              pageSize,
              total: filteredTotal,
              showSizeChanger: true,
              pageSizeOptions: ["20", "50", "100"],
              onChange: (page: number, nextPageSize: number) =>
                setFilters((prev) => ({
                  ...prev,
                  page,
                  page_size: nextPageSize,
                })),
            }}
          />
        )}
      </Card>

      <Drawer
        title={activeQuestionId ? `题目 #${activeQuestionId}` : "题目详情"}
        width={880}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setSearchParams((params) => {
            params.delete("question_id");
            return params;
          });
        }}
        destroyOnClose
      >
        {detailLoading ? (
          <Result icon={<Spin size="large" />} title="正在加载题目详情" />
        ) : detail ? (
          <QuestionDetailDrawerContent
            detail={detail}
            viewMode={detailViewMode}
            onViewModeChange={setDetailViewMode}
            adminReview={adminReview}
          />
        ) : (
          <Empty description="未找到题目详情" />
        )}
      </Drawer>
    </Space>
  );
}

function consensusColor(value: string) {
  if (value === "UNANIMOUS") return "green";
  if (value === "MAJORITY") return "blue";
  if (value === "DISPUTED") return "red";
  return "default";
}
