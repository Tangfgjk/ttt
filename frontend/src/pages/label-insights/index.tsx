import { EditOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";

import { usePageHashScroll } from "@/app/use-page-hash-scroll";
import { useAuthStore } from "@/app/store/auth-store";
import { QuestionDetailSections } from "@/components/question-detail-sections";
import { getConfidenceLevelLabel } from "@/constants/confidence-level";
import {
  useAdminQuestionReview,
  useOverrideAdminQuestionReview,
} from "@/modules/annotations/hooks";
import {
  useCognitiveLevels,
  useCompetencies,
  useGrades,
  useQuestionDetail,
  useQuestionTypes,
  useSubjects,
} from "@/modules/question-bank/hooks";
import { getAnnotatedOverview, getAnnotatedQuestions } from "@/services/visualization";
import type { AdminAggregateOverrideRequest, AnnotationAggregate } from "@/types/annotations";
import type { CompetencyItem, GradeItem } from "@/types/dictionary";
import type {
  AnnotatedDistributionBucket,
  AnnotatedOverview,
  AnnotatedQuestionListItem,
} from "@/types/visualization";

type ViewMode = "results" | "analysis";
type MetricMode = "count" | "ratio";

type ResultFilterValues = {
  keyword?: string;
  subject_id?: number;
  edu_stage?: string;
  grade_id?: number;
  question_type_id?: number;
  result_source?: string;
};

type AnalysisFilterValues = {
  keyword?: string;
  subject_id?: number;
  edu_stage?: string;
  question_type_id?: number;
  result_source?: string;
};

type EditFormValues = {
  final_cognitive_level_id?: number;
  review_comment?: string;
  competencies?: Record<number, number>;
};

type ChartDatum = AnnotatedDistributionBucket & {
  value: number;
  ratio: number;
  color: string;
};

const viewOptions = [
  { label: "标注结果", value: "results" },
  { label: "结果分析", value: "analysis" },
] as const;

const resultSourceOptions = [
  { label: "全部结果", value: "all" },
  { label: "金标", value: "gold" },
  { label: "最终标注", value: "aggregate" },
];

const metricOptions = [
  { label: "数量", value: "count" },
  { label: "比例", value: "ratio" },
];

const stageOptions = [
  { label: "初中", value: "junior" },
  { label: "高中", value: "senior" },
];

const chartPalette = [
  "#1677ff",
  "#13c2c2",
  "#722ed1",
  "#fa8c16",
  "#eb2f96",
  "#52c41a",
  "#2f54eb",
  "#fa541c",
  "#14b8a6",
  "#a855f7",
];

const cognitiveOrder = ["识记", "理解", "应用", "分析", "综合", "评价"];

const STAGE_COMPETENCY_CODES: Record<string, string[]> = {
  junior: [
    "abstraction",
    "operation",
    "geometric_intuition",
    "spatial_conception",
    "reasoning",
    "data_consciousness",
    "model_consciousness",
    "application_awareness",
    "innovation_awareness",
  ],
  senior: [
    "mathematical_abstraction",
    "logical_reasoning",
    "mathematical_modeling",
    "intuitive_imagination",
    "mathematical_operation",
    "data_analysis",
  ],
};

function formatAgreement(value?: number | null) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(2);
}

function stageLabel(stage?: string | null) {
  if (stage === "junior") return "初中";
  if (stage === "senior") return "高中";
  return "-";
}

function getStageGrades(grades: GradeItem[], stage?: string) {
  if (!stage) return grades;
  return grades.filter((item) => item.edu_stage === stage);
}

function getStageCompetencies(allCompetencies: CompetencyItem[], stage?: string | null) {
  const codes = stage ? STAGE_COMPETENCY_CODES[stage] ?? [] : [];
  if (!codes.length) return allCompetencies;
  const order = new Map(codes.map((code, index) => [code, index]));
  return allCompetencies
    .filter((item) => order.has(item.code))
    .sort((a, b) => (order.get(a.code) ?? 999) - (order.get(b.code) ?? 999));
}

function competencyLevelTagColor(levelValue: number) {
  if (levelValue >= 3) return "magenta";
  if (levelValue === 2) return "purple";
  if (levelValue === 1) return "processing";
  return "default";
}

function sortCognitiveDistribution(items: AnnotatedDistributionBucket[]) {
  const order = new Map(cognitiveOrder.map((label, index) => [label, index]));
  return [...items].sort((a, b) => {
    const indexA = order.get(a.label);
    const indexB = order.get(b.label);
    if (indexA !== undefined && indexB !== undefined) return indexA - indexB;
    if (indexA !== undefined) return -1;
    if (indexB !== undefined) return 1;
    return b.count - a.count;
  });
}

function sortDistributionByCount(items: AnnotatedDistributionBucket[]) {
  return [...items].sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return a.label.localeCompare(b.label, "zh-CN");
  });
}

function sortLevelDistribution(items: AnnotatedDistributionBucket[]) {
  return [...items].sort((a, b) => {
    const matchA = a.label.match(/L(\d+)/);
    const matchB = b.label.match(/L(\d+)/);
    const levelA = matchA ? Number(matchA[1]) : 999;
    const levelB = matchB ? Number(matchB[1]) : 999;
    return levelA - levelB;
  });
}

function buildChartData(
  items: AnnotatedDistributionBucket[],
  mode: MetricMode,
  denominator: number,
) {
  return items.map((item, index) => {
    const ratio = Number((((item.count || 0) / Math.max(denominator, 1)) * 100).toFixed(2));
    return {
      ...item,
      value: mode === "ratio" ? ratio : item.count,
      ratio,
      color: chartPalette[index % chartPalette.length],
    } satisfies ChartDatum;
  });
}

function useDistributionChart(params: {
  ref: React.RefObject<HTMLDivElement | null>;
  title: string;
  items: ChartDatum[];
  mode: MetricMode;
  emptyText: string;
  selectedKey?: string | null;
  onClick?: (item: AnnotatedDistributionBucket) => void;
}) {
  const { ref, title, items, mode, emptyText, selectedKey, onClick } = params;

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const chartWidth = ref.current.clientWidth;
    const compactPie = chartWidth < 620 || items.length > 6;
    const hasManySlices = items.length > 5;

    if (!items.length) {
      chart.setOption({
        animation: false,
        title: {
          text: emptyText,
          left: "center",
          top: "middle",
          textStyle: {
            fontSize: 14,
            fontWeight: 400,
            color: "#8c8c8c",
          },
        },
      });
    } else if (mode === "ratio") {
      chart.setOption({
        animation: false,
        tooltip: {
          trigger: "item",
          formatter: (item: { data?: ChartDatum }) => {
            const data = item.data;
            if (!data) return "";
            return `${data.label}<br/>占比：${data.ratio}%<br/>数量：${data.count}`;
          },
        },
        series: [
          {
            name: title,
            type: "pie",
            radius: compactPie ? ["42%", "74%"] : ["50%", "82%"],
            center: ["50%", "54%"],
            minAngle: compactPie ? 6 : 4,
            avoidLabelOverlap: true,
            selectedMode: onClick ? "single" : false,
            label: {
              show: !compactPie || !hasManySlices,
              formatter: compactPie ? "{d}%" : "{b}\n{d}%",
              color: "#17252f",
              fontSize: compactPie ? 11 : 12,
              overflow: "truncate",
              width: compactPie ? 44 : 76,
            },
            labelLine: {
              show: !compactPie || items.length <= 4,
              length: compactPie ? 8 : 12,
              length2: compactPie ? 4 : 8,
            },
            emphasis: {
              scale: true,
              scaleSize: compactPie ? 5 : 8,
            },
            data: items.map((item) => ({
              ...item,
              name: item.label,
              value: item.ratio,
              selected: item.key === selectedKey,
              itemStyle: {
                color: item.color,
                borderColor: "#ffffff",
                borderWidth: 2,
              },
            })),
          },
        ],
      });
    } else {
      chart.setOption({
        animation: false,
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (seriesItems: Array<{ data?: ChartDatum }>) => {
            const data = seriesItems[0]?.data;
            if (!data) return "";
            return `${data.label}<br/>数量：${data.count}`;
          },
        },
        grid: { top: 18, left: 16, right: 18, bottom: 56, containLabel: true },
        xAxis: {
          type: "category",
          data: items.map((item) => item.label),
          axisLabel: {
            interval: 0,
            rotate: items.length > 5 ? 22 : 0,
            color: "rgba(23, 37, 47, 0.68)",
          },
          axisLine: { lineStyle: { color: "rgba(23, 37, 47, 0.18)" } },
        },
        yAxis: {
          type: "value",
          name: "题数",
          nameTextStyle: { color: "rgba(23, 37, 47, 0.56)" },
          splitLine: { lineStyle: { color: "rgba(23, 37, 47, 0.08)" } },
        },
        series: [
          {
            name: title,
            type: "bar",
            barMaxWidth: 56,
            data: items.map((item) => ({
              ...item,
              itemStyle: {
                color: item.color,
                borderRadius: [8, 8, 0, 0],
                opacity: selectedKey && item.key !== selectedKey ? 0.45 : 0.94,
                borderColor: item.key === selectedKey ? "#17252f" : item.color,
                borderWidth: item.key === selectedKey ? 1.5 : 0,
              },
            })),
          },
        ],
      });
    }

    const handleResize = () => chart.resize();
    const handleClick = (event: { data?: unknown }) => {
      const payload = event.data as AnnotatedDistributionBucket | undefined;
      if (payload && onClick) onClick(payload);
    };

    window.addEventListener("resize", handleResize);
    chart.off("click");
    chart.on("click", handleClick);
    chart.resize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.off("click", handleClick);
      chart.dispose();
    };
  }, [emptyText, items, mode, onClick, ref, selectedKey, title]);
}

function DistributionLegend({
  items,
  selectedKey,
  onSelect,
}: {
  items: ChartDatum[];
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="label-insights-legend">
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          className={`label-insights-legend__item${
            item.key === selectedKey ? " label-insights-legend__item--active" : ""
          }`}
          onClick={() => onSelect?.(item.key)}
        >
          <span
            className="label-insights-legend__swatch"
            style={{ backgroundColor: item.color }}
          />
          <span className="label-insights-legend__label">{item.label}</span>
        </button>
      ))}
    </div>
  );
}

function SummaryCards({
  overview,
  loading,
  showAverage = false,
}: {
  overview?: AnnotatedOverview;
  loading: boolean;
  showAverage?: boolean;
}) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={12} xl={showAverage ? 4 : 6}>
        <Card className="label-insights-kpi">
          <Statistic title="标注结果总量" value={overview?.total_labeled_questions ?? 0} loading={loading} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={showAverage ? 4 : 6}>
        <Card className="label-insights-kpi">
          <Statistic title="当前筛选结果" value={overview?.filtered_question_count ?? 0} loading={loading} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={showAverage ? 4 : 6}>
        <Card className="label-insights-kpi">
          <Statistic title="金标题数" value={overview?.gold_labeled_questions ?? 0} loading={loading} />
        </Card>
      </Col>
      <Col xs={24} sm={12} xl={showAverage ? 4 : 6}>
        <Card className="label-insights-kpi">
          <Statistic title="最终标注题数" value={overview?.aggregate_labeled_questions ?? 0} loading={loading} />
        </Card>
      </Col>
      {showAverage ? (
        <Col xs={24} sm={12} xl={4}>
          <Card className="label-insights-kpi">
            <Statistic title="平均一致率" value={overview?.average_agreement_score ?? 0} precision={2} loading={loading} />
          </Card>
        </Col>
      ) : null}
    </Row>
  );
}

export function LabelInsightsPage() {
  usePageHashScroll();

  const session = useAuthStore((state) => state.session);
  const adminUserId = session?.role === "admin" ? session.id : null;

  const [viewMode, setViewMode] = useState<ViewMode>("results");
  const [resultForm] = Form.useForm();
  const [analysisForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const selectedResultStage = Form.useWatch("edu_stage", resultForm);

  const [resultFilters, setResultFilters] = useState<ResultFilterValues>({ result_source: "all" });
  const [analysisFilters, setAnalysisFilters] = useState<AnalysisFilterValues>({ result_source: "all" });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedQuestion, setSelectedQuestion] = useState<AnnotatedQuestionListItem | null>(null);

  const [cognitiveMode, setCognitiveMode] = useState<MetricMode>("count");
  const [competencyMode, setCompetencyMode] = useState<MetricMode>("count");
  const [levelMode, setLevelMode] = useState<MetricMode>("count");
  const [selectedCompetencyKey, setSelectedCompetencyKey] = useState<string | null>(null);

  const cognitiveRef = useRef<HTMLDivElement | null>(null);
  const competencyRef = useRef<HTMLDivElement | null>(null);
  const levelRef = useRef<HTMLDivElement | null>(null);

  const subjectsQuery = useSubjects();
  const gradesQuery = useGrades();
  const questionTypesQuery = useQuestionTypes();
  const cognitiveLevelsQuery = useCognitiveLevels();
  const competenciesQuery = useCompetencies();

  const resultOverviewQuery = useQuery({
    queryKey: ["label-insights", "results-overview", resultFilters],
    queryFn: () => getAnnotatedOverview(resultFilters),
    placeholderData: (previousData) => previousData,
  });

  const resultListQuery = useQuery({
    queryKey: ["label-insights", "results-list", resultFilters, page, pageSize],
    queryFn: () => getAnnotatedQuestions({ ...resultFilters, page, page_size: pageSize }),
    placeholderData: (previousData) => previousData,
  });

  const analysisReady = Boolean(analysisFilters.subject_id && analysisFilters.edu_stage);
  const analysisOverviewQuery = useQuery({
    queryKey: ["label-insights", "analysis-overview", analysisFilters],
    queryFn: () => getAnnotatedOverview(analysisFilters),
    enabled: analysisReady,
    placeholderData: (previousData) => previousData,
  });

  const questionDetailQuery = useQuestionDetail(selectedQuestion?.question_id ?? null);
  const reviewQuery = useAdminQuestionReview(selectedQuestion?.question_id ?? null, adminUserId);
  const overrideMutation = useOverrideAdminQuestionReview(selectedQuestion?.question_id ?? null);

  const editStage = selectedQuestion?.edu_stage ?? null;
  const visibleCompetencies = useMemo(
    () => getStageCompetencies(competenciesQuery.data ?? [], editStage),
    [competenciesQuery.data, editStage],
  );

  const effectiveResult: AnnotationAggregate | null =
    reviewQuery.data?.aggregate ?? reviewQuery.data?.gold_label ?? null;

  useEffect(() => {
    if (!effectiveResult) return;
    const competencyMap = Object.fromEntries(
      visibleCompetencies.map((item) => [
        item.id,
        effectiveResult.competencies.find((competency) => competency.competency_id === item.id)?.level_value ?? 0,
      ]),
    );
    editForm.setFieldsValue({
      final_cognitive_level_id: effectiveResult.final_cognitive_level_id ?? undefined,
      competencies: competencyMap,
      review_comment: undefined,
    });
  }, [editForm, effectiveResult, visibleCompetencies]);

  const sortedCognitive = useMemo(
    () => sortCognitiveDistribution(analysisOverviewQuery.data?.cognitive_level_distribution ?? []),
    [analysisOverviewQuery.data?.cognitive_level_distribution],
  );
  const sortedCompetencies = useMemo(
    () => sortDistributionByCount(analysisOverviewQuery.data?.competency_distribution ?? []),
    [analysisOverviewQuery.data?.competency_distribution],
  );

  const selectedCompetency = useMemo(() => {
    if (!sortedCompetencies.length) return null;
    return sortedCompetencies.find((item) => item.key === selectedCompetencyKey) ?? sortedCompetencies[0];
  }, [selectedCompetencyKey, sortedCompetencies]);

  useEffect(() => {
    if (!sortedCompetencies.length) {
      setSelectedCompetencyKey(null);
      return;
    }
    if (!selectedCompetencyKey || !sortedCompetencies.some((item) => item.key === selectedCompetencyKey)) {
      setSelectedCompetencyKey(sortedCompetencies[0].key);
    }
  }, [selectedCompetencyKey, sortedCompetencies]);

  const filteredLevelItems = useMemo(() => {
    const items = analysisOverviewQuery.data?.competency_level_distribution ?? [];
    if (!selectedCompetency) return [];
    return sortLevelDistribution(
      items.filter((item) => item.key.startsWith(`${selectedCompetency.key}_L`)),
    );
  }, [analysisOverviewQuery.data?.competency_level_distribution, selectedCompetency]);

  const analysisTotal = analysisOverviewQuery.data?.filtered_question_count ?? 0;
  const selectedCompetencyTotal = selectedCompetency?.count ?? 0;

  const cognitiveChartItems = useMemo(
    () => buildChartData(sortedCognitive, cognitiveMode, analysisTotal),
    [analysisTotal, cognitiveMode, sortedCognitive],
  );
  const competencyChartItems = useMemo(
    () => buildChartData(sortedCompetencies, competencyMode, analysisTotal),
    [analysisTotal, competencyMode, sortedCompetencies],
  );
  const levelChartItems = useMemo(
    () => buildChartData(filteredLevelItems, levelMode, selectedCompetencyTotal),
    [filteredLevelItems, levelMode, selectedCompetencyTotal],
  );

  useDistributionChart({
    ref: cognitiveRef,
    title: "认知层级",
    items: cognitiveChartItems,
    mode: cognitiveMode,
    emptyText: analysisReady ? "暂无认知层级数据" : "请先选择学科和学段",
  });

  useDistributionChart({
    ref: competencyRef,
    title: "核心素养",
    items: competencyChartItems,
    mode: competencyMode,
    emptyText: analysisReady ? "暂无核心素养数据" : "请先选择学科和学段",
    selectedKey: selectedCompetencyKey,
    onClick: (item) => setSelectedCompetencyKey(item.key),
  });

  useDistributionChart({
    ref: levelRef,
    title: "素养层级",
    items: levelChartItems,
    mode: levelMode,
    emptyText: analysisReady ? "点击左侧某个核心素养查看层级分布" : "请先选择学科和学段",
    selectedKey: selectedCompetencyKey,
  });

  const handleResultSearch = (values: ResultFilterValues) => {
    setPage(1);
    setResultFilters({
      keyword: values.keyword?.trim() || undefined,
      subject_id: values.subject_id || undefined,
      edu_stage: values.edu_stage || undefined,
      grade_id: values.grade_id || undefined,
      question_type_id: values.question_type_id || undefined,
      result_source: values.result_source || "all",
    });
  };

  const handleAnalysisSearch = (values: AnalysisFilterValues) => {
    setAnalysisFilters({
      keyword: values.keyword?.trim() || undefined,
      subject_id: values.subject_id || undefined,
      edu_stage: values.edu_stage || undefined,
      question_type_id: values.question_type_id || undefined,
      result_source: values.result_source || "all",
    });
    setSelectedCompetencyKey(null);
  };

  const handleOverrideSubmit = async (values: EditFormValues) => {
    if (!selectedQuestion || adminUserId === null) return;
    const competencies = visibleCompetencies
      .map((item) => ({
        competency_id: item.id,
        level_value: values.competencies?.[item.id] ?? 0,
      }))
      .filter((item) => item.level_value > 0);
    const payload: AdminAggregateOverrideRequest = {
      admin_user_id: adminUserId,
      final_cognitive_level_id: values.final_cognitive_level_id ?? null,
      competencies,
      review_comment: values.review_comment?.trim() || null,
    };
    await overrideMutation.mutateAsync(payload);
    message.success("标注结果已更新");
  };

  const resultColumns = [
    {
      title: "题目",
      key: "stem_preview",
      render: (_value: unknown, row: AnnotatedQuestionListItem) => (
        <Space direction="vertical" size={2}>
          <Typography.Text strong>#{row.question_id}</Typography.Text>
          <Typography.Text type="secondary">{row.stem_preview}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "学科 / 学段 / 年级",
      key: "subject",
      width: 180,
      render: (_value: unknown, row: AnnotatedQuestionListItem) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{row.subject_name}</Typography.Text>
          <Typography.Text type="secondary">
            {stageLabel(row.edu_stage)} / {row.grade_name ?? "-"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "题型",
      dataIndex: "question_type_name",
      width: 110,
      render: (value?: string | null) => value ?? "-",
    },
    {
      title: "结果来源",
      dataIndex: "result_source_label",
      width: 100,
      render: (value: string) => <Tag color={value === "金标" ? "gold" : "blue"}>{value}</Tag>,
    },
    {
      title: "认知层级",
      dataIndex: "final_cognitive_level_name",
      width: 110,
      render: (value?: string | null) => value ?? "-",
    },
    {
      title: "核心素养",
      key: "competencies",
      render: (_value: unknown, row: AnnotatedQuestionListItem) => (
        <Space size={[4, 4]} wrap>
          {row.competencies.filter((item) => item.level_value > 0).map((item) => (
            <Tag key={`${row.question_id}-${item.competency_id}`} color="processing">
              {item.competency_name} L{item.level_value}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "一致率",
      dataIndex: "agreement_score",
      width: 90,
      render: (value?: number | null) => formatAgreement(value),
    },
    {
      title: "操作",
      key: "action",
      width: 90,
      render: (_value: unknown, row: AnnotatedQuestionListItem) => (
        <Button type="link" icon={<EditOutlined />} onClick={() => setSelectedQuestion(row)}>
          审查
        </Button>
      ),
    },
  ];

  const gradesForResult = getStageGrades(gradesQuery.data ?? [], selectedResultStage);

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }} className="label-insights-page">
      <Card id="label-insights-overview" className="page-section-anchor label-insights-hero">
        <div className="label-insights-hero__content">
          <div className="label-insights-hero__copy">
            <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
              标注结果分析
            </Typography.Title>
            <Typography.Text type="secondary">
              统一查看标注结果，并按学科与学段切换到更清晰的分布分析视图。
            </Typography.Text>
          </div>
          <div className="label-insights-hero__nav">
            <div className="label-insights-hero__nav-label">视图切换</div>
            <Segmented
              className="label-insights-hero__switch"
              options={viewOptions}
              value={viewMode}
              onChange={(value: string | number) => setViewMode(value as ViewMode)}
            />
            <div className="label-insights-hero__nav-hint">点击按钮即可切换，建议先看“结果分析”。</div>
          </div>
        </div>
        <div className="label-insights-hero__guide">
          <div className="label-insights-hero__guide-card">
            <Typography.Text strong>标注结果</Typography.Text>
            <Typography.Text type="secondary">查看列表、筛选结果并进入单题审查。</Typography.Text>
          </div>
          <div className="label-insights-hero__guide-card">
            <Typography.Text strong>结果分析</Typography.Text>
            <Typography.Text type="secondary">查看分布图、比例切换和核心素养联动钻取。</Typography.Text>
          </div>
        </div>
      </Card>

      {viewMode === "results" ? (
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <SummaryCards overview={resultOverviewQuery.data} loading={resultOverviewQuery.isLoading} />

          <Card className="page-section-anchor label-insights-filter-card">
            <Form
              form={resultForm}
              layout="vertical"
              onFinish={handleResultSearch}
              initialValues={{ result_source: "all" }}
            >
              <Row gutter={[16, 8]}>
                <Col xs={24} md={8} lg={7}>
                  <Form.Item label="关键词" name="keyword">
                    <Input allowClear placeholder="搜索题干关键词" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={3}>
                  <Form.Item label="学科" name="subject_id">
                    <Select
                      allowClear
                      placeholder="全部学科"
                      options={(subjectsQuery.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={3}>
                  <Form.Item label="学段" name="edu_stage">
                    <Select allowClear placeholder="全部学段" options={stageOptions} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={3}>
                  <Form.Item label="年级" name="grade_id">
                    <Select
                      allowClear
                      placeholder="全部年级"
                      options={gradesForResult.map((item) => ({
                        value: item.id,
                        label: item.grade_name,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={4}>
                  <Form.Item label="题型" name="question_type_id">
                    <Select
                      allowClear
                      placeholder="全部题型"
                      options={(questionTypesQuery.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={4}>
                  <Form.Item label="结果来源" name="result_source">
                    <Select options={resultSourceOptions} />
                  </Form.Item>
                </Col>
              </Row>
              <Space wrap>
                <Button type="primary" htmlType="submit">
                  应用筛选
                </Button>
                <Button
                  onClick={() => {
                    resultForm.resetFields();
                    setPage(1);
                    setResultFilters({ result_source: "all" });
                  }}
                >
                  重置
                </Button>
              </Space>
            </Form>
          </Card>

          <Card id="label-insights-review" className="page-section-anchor" title="标注结果">
            <Table<AnnotatedQuestionListItem>
              rowKey="question_id"
              loading={resultListQuery.isLoading}
              columns={resultColumns}
              dataSource={resultListQuery.data?.items ?? []}
              scroll={{ x: 1380 }}
              pagination={{
                current: resultListQuery.data?.meta.page ?? page,
                pageSize: resultListQuery.data?.meta.page_size ?? pageSize,
                total: resultListQuery.data?.meta.total ?? 0,
                showSizeChanger: true,
                pageSizeOptions: ["10", "20", "50"],
                onChange: (nextPage: number, nextPageSize: number) => {
                  setPage(nextPage);
                  setPageSize(nextPageSize);
                },
              }}
            />
          </Card>
        </Space>
      ) : (
        <Space direction="vertical" size={20} style={{ width: "100%" }}>
          <Card id="label-insights-distribution" className="page-section-anchor label-insights-filter-card">
            <Form
              form={analysisForm}
              layout="vertical"
              onFinish={handleAnalysisSearch}
              initialValues={{ result_source: "all" }}
            >
              <Row gutter={[16, 8]}>
                <Col xs={24} md={8} lg={4}>
                  <Form.Item label="学科" name="subject_id" rules={[{ required: true, message: "请选择学科" }]}>
                    <Select
                      placeholder="请选择学科"
                      options={(subjectsQuery.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={4}>
                  <Form.Item label="学段" name="edu_stage" rules={[{ required: true, message: "请选择学段" }]}>
                    <Select placeholder="请选择学段" options={stageOptions} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={6}>
                  <Form.Item label="关键词" name="keyword">
                    <Input allowClear placeholder="搜索题干关键词" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={5}>
                  <Form.Item label="题型" name="question_type_id">
                    <Select
                      allowClear
                      placeholder="全部题型"
                      options={(questionTypesQuery.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.name,
                      }))}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8} lg={5}>
                  <Form.Item label="结果来源" name="result_source">
                    <Select options={resultSourceOptions} />
                  </Form.Item>
                </Col>
              </Row>
              <Space wrap>
                <Button type="primary" htmlType="submit">
                  应用筛选
                </Button>
                <Button
                  onClick={() => {
                    analysisForm.resetFields();
                    setAnalysisFilters({ result_source: "all" });
                    setSelectedCompetencyKey(null);
                  }}
                >
                  重置
                </Button>
              </Space>
            </Form>
          </Card>

          <SummaryCards
            overview={analysisOverviewQuery.data}
            loading={analysisOverviewQuery.isLoading}
            showAverage
          />

          {!analysisReady ? (
            <Card>
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择学科和学段后查看分布分析" />
            </Card>
          ) : (
            <Row gutter={[16, 16]} className="label-insights-analysis-grid">
              <Col xs={24} xl={12}>
                <Card
                  className="label-insights-chart-card"
                  title="认知层级分布"
                  extra={
                    <Segmented
                      size="small"
                      options={metricOptions}
                      value={cognitiveMode}
                      onChange={(value: string | number) => setCognitiveMode(value as MetricMode)}
                    />
                  }
                >
                  <div className="label-insights-chart-panel">
                    <div className="label-insights-chart-panel__meta">
                      <DistributionLegend items={cognitiveChartItems} />
                    </div>
                    <div className="label-insights-chart-panel__canvas">
                      <div ref={cognitiveRef} style={{ width: "100%", height: 360 }} />
                    </div>
                  </div>
                </Card>
              </Col>

              <Col xs={24} xl={12}>
                <Card
                  className="label-insights-chart-card"
                  title="核心素养分布"
                  extra={
                    <Segmented
                      size="small"
                      options={metricOptions}
                      value={competencyMode}
                      onChange={(value: string | number) => setCompetencyMode(value as MetricMode)}
                    />
                  }
                >
                  <div className="label-insights-chart-panel">
                    <div className="label-insights-chart-panel__meta">
                      <div className="label-insights-chart-card__hint">
                        默认选中当前样本量最高的核心素养，点击图表或图例可切换。
                      </div>
                      <DistributionLegend
                        items={competencyChartItems}
                        selectedKey={selectedCompetencyKey}
                        onSelect={setSelectedCompetencyKey}
                      />
                    </div>
                    <div className="label-insights-chart-panel__canvas">
                      <div ref={competencyRef} style={{ width: "100%", height: 360 }} />
                    </div>
                  </div>
                </Card>
              </Col>

              <Col xs={24} xl={12}>
                <Card className="label-insights-focus-card" title="当前聚焦">
                  {selectedCompetency ? (
                    <div className="label-insights-focus-card__panel">
                      <div className="label-insights-focus-card__chip">
                        <span
                          className="label-insights-focus-card__dot"
                          style={{
                            backgroundColor:
                              competencyChartItems.find((item) => item.key === selectedCompetency.key)?.color ??
                              chartPalette[0],
                          }}
                        />
                        <Typography.Text strong>{selectedCompetency.label}</Typography.Text>
                      </div>
                      <div className="label-insights-focus-card__metrics">
                        <div className="label-insights-focus-card__metric">
                          <div className="label-insights-focus-card__metric-label">题目数量</div>
                          <div className="label-insights-focus-card__metric-value">{selectedCompetency.count}</div>
                        </div>
                        <div className="label-insights-focus-card__metric">
                          <div className="label-insights-focus-card__metric-label">当前占比</div>
                          <div className="label-insights-focus-card__metric-value">
                            {analysisTotal ? `${((selectedCompetency.count / analysisTotal) * 100).toFixed(2)}%` : "-"}
                          </div>
                        </div>
                      </div>
                      <div className="label-insights-chart-panel__meta">
                        <div className="label-insights-chart-card__hint">
                          默认按样本量从高到低排序，切换图例或点击图表可重新聚焦核心素养。
                        </div>
                      </div>
                      <div className="label-insights-focus-card__levels">
                        {levelChartItems.map((item) => (
                          <div key={item.key} className="label-insights-focus-card__level">
                            <span
                              className="label-insights-focus-card__level-dot"
                              style={{ backgroundColor: item.color }}
                            />
                            <span className="label-insights-focus-card__level-label">{item.label}</span>
                            <span className="label-insights-focus-card__level-value">{item.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可聚焦的核心素养" />
                  )}
                </Card>
              </Col>

              <Col xs={24} xl={12}>
                <Card
                  className="label-insights-chart-card"
                  title={selectedCompetency ? `${selectedCompetency.label}层级分布` : "核心素养层级分布"}
                  extra={
                    <Segmented
                      size="small"
                      options={metricOptions}
                      value={levelMode}
                      onChange={(value: string | number) => setLevelMode(value as MetricMode)}
                    />
                  }
                >
                  <div className="label-insights-chart-panel">
                    <div className="label-insights-chart-panel__meta">
                      <DistributionLegend items={levelChartItems} />
                    </div>
                    <div className="label-insights-chart-panel__canvas">
                      <div ref={levelRef} style={{ width: "100%", height: 360 }} />
                    </div>
                  </div>
                </Card>
              </Col>
            </Row>
          )}
        </Space>
      )}

      <Drawer
        title={selectedQuestion ? `标注结果审查 #${selectedQuestion.question_id}` : "标注结果审查"}
        width={920}
        open={selectedQuestion !== null}
        onClose={() => {
          setSelectedQuestion(null);
          editForm.resetFields();
        }}
        destroyOnClose
      >
        {!selectedQuestion ? null : (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card size="small" title="题目详情" loading={questionDetailQuery.isLoading}>
              {questionDetailQuery.data ? (
                <QuestionDetailSections detail={questionDetailQuery.data} />
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未找到题目详情" />
              )}
            </Card>

            <Card size="small" title="题目摘要">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="题目 ID">#{selectedQuestion.question_id}</Descriptions.Item>
                <Descriptions.Item label="结果来源">{selectedQuestion.result_source_label}</Descriptions.Item>
                <Descriptions.Item label="学科">{selectedQuestion.subject_name}</Descriptions.Item>
                <Descriptions.Item label="学段">{stageLabel(selectedQuestion.edu_stage)}</Descriptions.Item>
                <Descriptions.Item label="年级">{selectedQuestion.grade_name ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="题型">{selectedQuestion.question_type_name ?? "-"}</Descriptions.Item>
                <Descriptions.Item label="一致率">{formatAgreement(selectedQuestion.agreement_score)}</Descriptions.Item>
                <Descriptions.Item label="题干摘要" span={2}>
                  {selectedQuestion.stem_preview}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card size="small" title="当前结果" loading={reviewQuery.isLoading}>
              {effectiveResult ? (
                <Space direction="vertical" size={10} style={{ width: "100%" }}>
                  <Typography.Text>
                    认知层级 ID: {effectiveResult.final_cognitive_level_id ?? "-"}
                  </Typography.Text>
                  <Space size={[8, 8]} wrap>
                    {effectiveResult.competencies.filter((item) => item.level_value > 0).map((item) => (
                      <Tag key={item.competency_id} color="processing">
                        {item.competency_name} L{item.level_value}
                      </Tag>
                    ))}
                  </Space>
                </Space>
              ) : (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无当前结果" />
              )}
            </Card>

            {(reviewQuery.data?.annotations?.length ?? 0) > 0 ? (
              <Card size="small" title="标注员提交记录">
                <Row gutter={[12, 12]}>
                  {(reviewQuery.data?.annotations ?? []).map((annotation) => (
                    <Col xs={24} lg={12} key={annotation.annotation_id}>
                      <Card size="small" className="label-insights-annotation-card">
                        <Space direction="vertical" size={10} style={{ width: "100%" }}>
                          <Space wrap>
                            <Typography.Text strong>{annotation.user_name}</Typography.Text>
                            <Tag>认知层级 {annotation.cognitive_level_id ?? "-"}</Tag>
                          </Space>
                          <Space wrap size={[6, 6]}>
                            {annotation.competencies.map((competency) => (
                              <Tag
                                key={`${annotation.annotation_id}-${competency.competency_id}`}
                                color={competencyLevelTagColor(competency.level_value)}
                                className={competency.level_value > 0 ? "label-insights-annotation-tag--active" : undefined}
                              >
                                {competency.competency_name} L{competency.level_value} · 信心等级
                                {getConfidenceLevelLabel(competency.confidence_level ?? 5)}
                              </Tag>
                            ))}
                          </Space>
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            ) : null}

            <Card size="small" title="管理员修改结果">
              <Form
                form={editForm}
                layout="vertical"
                onFinish={(values: EditFormValues) => void handleOverrideSubmit(values)}
              >
                <Form.Item label="最终认知层级" name="final_cognitive_level_id">
                  <Select
                    allowClear
                    placeholder="请选择认知层级"
                    options={(cognitiveLevelsQuery.data ?? []).map((item) => ({
                      value: item.id,
                      label: item.name,
                    }))}
                  />
                </Form.Item>
                <Typography.Text strong>核心素养等级</Typography.Text>
                <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
                  {visibleCompetencies.map((item) => (
                    <Col xs={24} md={12} key={item.id}>
                      <Card size="small">
                        <Space direction="vertical" size={8} style={{ width: "100%" }}>
                          <Typography.Text strong>{item.name}</Typography.Text>
                          <Form.Item name={["competencies", item.id]} style={{ marginBottom: 0 }}>
                            <Select
                              options={[
                                { value: 0, label: "0 不标注" },
                                { value: 1, label: "1" },
                                { value: 2, label: "2" },
                                { value: 3, label: "3" },
                              ]}
                            />
                          </Form.Item>
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>
                <Form.Item label="修改说明" name="review_comment" style={{ marginTop: 16 }}>
                  <Input.TextArea rows={3} placeholder="记录这次人工修正的原因" />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={overrideMutation.isPending}>
                  保存结果
                </Button>
              </Form>
            </Card>
          </Space>
        )}
      </Drawer>
    </Space>
  );
}
