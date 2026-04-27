import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import {
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
import { useState } from "react";

import { QuestionRichText } from "@/components/question-rich-text";
import {
  useGrades,
  useQuestionDetail,
  useQuestionList,
  useQuestionOverview,
  useQuestionTypes,
  useSubjects,
} from "@/modules/question-bank/hooks";
import type { QuestionDetail, QuestionListItem, QuestionListParams } from "@/types/question";

const DEFAULT_PAGE_SIZE = 20;

const annotationStatusOptions = [
  { label: "全部状态", value: "" },
  { label: "待标注", value: "PENDING" },
  { label: "标注中", value: "ANNOTATING" },
  { label: "已完成", value: "COMPLETED" },
  { label: "有争议", value: "DISPUTED" },
];

const detailViewModeOptions = [
  { label: "渲染视图", value: "rendered" },
  { label: "原始文本", value: "raw" },
] as const;

type DetailViewMode = (typeof detailViewModeOptions)[number]["value"];

const statusColorMap: Record<string, string> = {
  PENDING: "gold",
  ANNOTATING: "blue",
  COMPLETED: "green",
  DISPUTED: "red",
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
}: {
  detail: QuestionDetail;
  viewMode: DetailViewMode;
  onViewModeChange: (value: DetailViewMode) => void;
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
    </Space>
  );
}

export function QuestionsPage() {
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

  const items = questionListQuery.data?.items ?? [];
  const pageMeta = questionListQuery.data?.meta;
  const overallTotal = overviewQuery.data?.meta.total ?? 0;
  const filteredTotal = pageMeta?.total ?? 0;
  const currentPage = pageMeta?.page ?? filters.page ?? 1;
  const pageSize = pageMeta?.page_size ?? filters.page_size ?? DEFAULT_PAGE_SIZE;
  const totalPages = Math.max(1, Math.ceil(filteredTotal / pageSize));

  const handleSearch = (values: {
    keyword?: string;
    subject_id?: number;
    grade_id?: number;
    question_type_id?: number;
    annotation_status?: string;
  }) => {
    setFilters({
      page: 1,
      page_size: pageSize,
      keyword: values.keyword?.trim() || undefined,
      subject_id: values.subject_id || undefined,
      grade_id: values.grade_id || undefined,
      question_type_id: values.question_type_id || undefined,
      annotation_status: values.annotation_status || undefined,
    });
  };

  const handleReset = () => {
    form.resetFields();
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
    {
      title: "题目 ID",
      dataIndex: "id",
      width: 110,
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
      width: 180,
    },
    {
      title: "标注状态",
      dataIndex: "annotation_status",
      width: 130,
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

  return (
    <>
      <Space direction="vertical" size={20} style={{ width: "100%" }}>
        <Card>
          <Typography.Title level={3} style={{ marginTop: 0 }}>
            统一题池
          </Typography.Title>
          <Typography.Paragraph type="secondary">
            这里展示的是统一 `question_id` 视角下的真实题库数据。列表里会做基础公式渲染，你可以直接展开行预览完整题干，或进入详情对照“渲染视图”和“原始文本”。
          </Typography.Paragraph>
        </Card>

        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="题池总题量" value={overallTotal} loading={overviewQuery.isLoading} suffix="题" />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="当前筛选命中" value={filteredTotal} loading={questionListQuery.isLoading} suffix="题" />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="当前页 / 总页数" value={`${currentPage} / ${totalPages}`} loading={questionListQuery.isLoading} />
            </Card>
          </Col>
        </Row>

        <Card title="筛选条件">
          <Form form={form} layout="vertical" onFinish={handleSearch}>
            <Row gutter={[16, 0]}>
              <Col xs={24} md={12} lg={8}>
                <Form.Item label="关键词搜索" name="keyword">
                  <Input allowClear placeholder="按题干关键词搜索" prefix={<SearchOutlined />} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12} lg={4}>
                <Form.Item label="学科" name="subject_id">
                  <Select
                    allowClear
                    placeholder="全部学科"
                    loading={subjectsQuery.isLoading}
                    options={(subjectsQuery.data ?? []).map((item) => ({
                      label: item.name,
                      value: item.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12} lg={4}>
                <Form.Item label="年级" name="grade_id">
                  <Select
                    allowClear
                    placeholder="全部年级"
                    loading={gradesQuery.isLoading}
                    options={(gradesQuery.data ?? []).map((item) => ({
                      label: item.grade_name,
                      value: item.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12} lg={4}>
                <Form.Item label="题型" name="question_type_id">
                  <Select
                    allowClear
                    placeholder="全部题型"
                    loading={questionTypesQuery.isLoading}
                    options={(questionTypesQuery.data ?? []).map((item) => ({
                      label: item.name,
                      value: item.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={12} lg={4}>
                <Form.Item label="标注状态" name="annotation_status">
                  <Select options={annotationStatusOptions} />
                </Form.Item>
              </Col>
            </Row>
            <Space>
              <Button type="primary" htmlType="submit">
                应用筛选
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置条件
              </Button>
            </Space>
          </Form>
        </Card>

        <Card>
          {questionListQuery.isError ? (
            <Result
              status="warning"
              title="统一题池数据加载失败"
              subTitle={questionListQuery.error instanceof Error ? questionListQuery.error.message : "请稍后重试。"}
              extra={
                <Button type="primary" onClick={() => void questionListQuery.refetch()}>
                  重新加载
                </Button>
              }
            />
          ) : !questionListQuery.isLoading && !items.length ? (
            <Empty description="当前筛选条件下没有题目数据" />
          ) : (
            <Table<QuestionListItem>
              rowKey="id"
              loading={questionListQuery.isLoading}
              columns={columns}
              dataSource={items}
              expandable={{
                expandedRowRender: (record: QuestionListItem) => (
                  <div className="question-expand-preview">
                    <Typography.Text strong>完整题干预览</Typography.Text>
                    <QuestionRichText
                      html={record.content?.stem_html}
                      text={record.content?.stem_text}
                      emptyLabel="暂无题干"
                    />
                  </div>
                ),
                rowExpandable: (record: QuestionListItem) => Boolean(record.content?.stem_text || record.content?.stem_html),
              }}
              pagination={{
                current: currentPage,
                pageSize,
                total: filteredTotal,
                showSizeChanger: true,
                pageSizeOptions: ["20", "50", "100"],
                showTotal: (total: number, range: [number, number]) => `显示 ${range[0]}-${range[1]} 条，共 ${total} 题`,
                onChange: (page: number, nextPageSize: number) => {
                  setFilters((previous) => ({
                    ...previous,
                    page,
                    page_size: nextPageSize,
                  }));
                },
              }}
              scroll={{ x: 1240 }}
            />
          )}
        </Card>
      </Space>

      <Drawer
        title={activeQuestionId ? `题目详情 #${activeQuestionId}` : "题目详情"}
        width={760}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnClose={false}
      >
        {questionDetailQuery.isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
            <Spin />
          </div>
        ) : questionDetailQuery.isError ? (
          <Result
            status="warning"
            title="题目详情加载失败"
            subTitle={questionDetailQuery.error instanceof Error ? questionDetailQuery.error.message : "请稍后重试。"}
            extra={
              <Button type="primary" onClick={() => void questionDetailQuery.refetch()}>
                重新加载
              </Button>
            }
          />
        ) : questionDetailQuery.data ? (
          <QuestionDetailDrawerContent
            detail={questionDetailQuery.data}
            viewMode={detailViewMode}
            onViewModeChange={setDetailViewMode}
          />
        ) : (
          <Empty description="暂无题目详情" />
        )}
      </Drawer>
    </>
  );
}
