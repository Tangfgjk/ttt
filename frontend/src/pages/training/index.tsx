import { Button, Card, Col, Descriptions, Drawer, Empty, Popconfirm, Row, Select, Space, Table, Tag, Tooltip, Typography } from "antd";
import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";
import { useNavigate } from "react-router-dom";

import { formatBackendDateTime as formatDateTime } from "@/app/date-time";
import { usePageHashScroll } from "@/app/use-page-hash-scroll";
import { useAuthStore } from "@/app/store/auth-store";
import { annotationStatusLabelMap } from "@/constants/annotation-status";
import { getRunStatusColor, getRunStatusLabel } from "@/constants/run-status";
import {
  useActiveLearningOverview,
  useActivateModelVersion,
} from "@/modules/active-learning/hooks";
import {
  useAnnotationPoolSummary,
  useResetAnnotationPools,
  useRollbackSelectionBatch,
  useSelectionBatches,
} from "@/modules/annotations/hooks";
import type {
  CoresetRun,
  ModelVersion,
  PredictionRun,
  TrainingEpoch,
  TrainingRun,
  TrendGroup,
} from "@/types/active-learning";
import type { AnnotationPoolStatus, SelectionBatchSummary, SelectionStrategy } from "@/types/annotations";

const coreSetAlgorithms = new Set<SelectionStrategy>([
  "moe",
  "kmeans",
  "facility_location",
  "graph_cut",
  "random",
]);

const poolStatusLabels: Record<AnnotationPoolStatus, string> = {
  PENDING: `${annotationStatusLabelMap.PENDING}池`,
  WAITING: `${annotationStatusLabelMap.WAITING}池`,
  IN_PROGRESS: `${annotationStatusLabelMap.IN_PROGRESS}池`,
  REVIEW_PENDING: `${annotationStatusLabelMap.REVIEW_PENDING}池`,
  COMPLETED: `${annotationStatusLabelMap.COMPLETED}池`,
};

export function TrainingPage() {
  usePageHashScroll();

  const navigate = useNavigate();
  const session = useAuthStore((state) => state.session);
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const trainingTableAnchorRef = useRef<HTMLDivElement | null>(null);
  const { data, isLoading } = useActiveLearningOverview();
  const { data: poolSummary, isLoading: isPoolSummaryLoading } = useAnnotationPoolSummary();
  const { data: selectionBatches = [] } = useSelectionBatches();
  const activateMutation = useActivateModelVersion();
  const resetPoolsMutation = useResetAnnotationPools();
  const rollbackSelectionBatchMutation = useRollbackSelectionBatch();
  const [selectedTrendGroupKey, setSelectedTrendGroupKey] = useState<string>();
  const [expandedTrainingRunKeys, setExpandedTrainingRunKeys] = useState<Key[]>([]);
  const [selectedCoresetRun, setSelectedCoresetRun] = useState<CoresetRun | null>(null);

  const trendGroups = data?.trend_groups ?? [];
  const trainingRuns = data?.training_runs ?? [];
  const modelVersions = data?.model_versions ?? [];
  const predictionRuns = data?.prediction_runs ?? [];
  const coresetRuns = data?.coreset_runs ?? [];

  useEffect(() => {
    if (!trendGroups.length) {
      setSelectedTrendGroupKey(undefined);
      return;
    }
    if (!selectedTrendGroupKey || !trendGroups.some((item) => item.key === selectedTrendGroupKey)) {
      setSelectedTrendGroupKey(trendGroups[0].key);
    }
  }, [selectedTrendGroupKey, trendGroups]);

  const selectedTrendGroup = useMemo<TrendGroup | null>(() => {
    if (!trendGroups.length) return null;
    return trendGroups.find((item) => item.key === selectedTrendGroupKey) ?? trendGroups[0];
  }, [selectedTrendGroupKey, trendGroups]);

  const trendSeries = useMemo(() => {
    const points = selectedTrendGroup?.points ?? [];
    return {
      labels: points.map((item) => item.sample_label),
      accuracy: points.map((item) => item.level_accuracy ?? 0),
      f1: points.map((item) => item.macro_f1 ?? 0),
      detection: points.map((item) => item.detection_rate ?? 0),
    };
  }, [selectedTrendGroup]);

  const poolCounts = useMemo(() => {
    return (poolSummary?.items ?? []).reduce<Record<string, number>>((acc, item) => {
      acc[item.status] = item.count;
      return acc;
    }, {});
  }, [poolSummary?.items]);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    chartInstanceRef.current = chart;
    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
      chartInstanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartInstanceRef.current;
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      grid: { top: 48, left: 36, right: 24, bottom: 48 },
      xAxis: {
        type: "category",
        data: trendSeries.labels,
        axisLabel: { interval: 0, rotate: trendSeries.labels.length > 6 ? 18 : 0 },
      },
      yAxis: { type: "value", min: 0, max: 1 },
      series: [
        { name: "Accuracy", type: "line", smooth: true, data: trendSeries.accuracy },
        { name: "Macro-F1", type: "line", smooth: true, data: trendSeries.f1 },
        { name: "Detection", type: "line", smooth: true, data: trendSeries.detection },
      ],
    });
    chart.resize();
  }, [trendSeries]);

  const focusTrainingRun = (runId: number) => {
    setExpandedTrainingRunKeys((prev) => Array.from(new Set([...prev, runId])));
    window.setTimeout(() => {
      trainingTableAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };

  const openQuestionSelection = (questionIds: number[], annotationStatus?: string) => {
    if (!questionIds.length) return;
    const params = new URLSearchParams();
    params.set("question_ids", questionIds.join(","));
    if (annotationStatus) {
      params.set("annotation_status", annotationStatus);
    }
    navigate(`/questions?${params.toString()}`);
  };

  const handleResetPools = async () => {
    if (!session) return;
    await resetPoolsMutation.mutateAsync({ admin_user_id: session.id });
  };

  const handleRollbackSelectionBatch = async (batchId: number) => {
    if (!session) return;
    await rollbackSelectionBatchMutation.mutateAsync({
      batchId,
      payload: { admin_user_id: session.id },
    });
  };

  const trainingColumns = [
    {
      title: "任务",
      key: "task",
      render: (_value: unknown, row: TrainingRun) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.run_display_name}</Typography.Text>
          <Typography.Text type="secondary">{row.run_no}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "对应模型",
      key: "model",
      render: (_value: unknown, row: TrainingRun) =>
        row.related_model_version_id ? (
          <Tooltip title={row.related_model_display_name ?? row.related_model_version_code}>
            <Button type="link" style={{ padding: 0 }} onClick={() => focusTrainingRun(row.id)}>
              {compactModelDisplayName(row.related_model_display_name ?? row.related_model_version_code)}
            </Button>
          </Tooltip>
        ) : (
          "-"
        ),
    },
    { title: "状态", dataIndex: "status", render: statusTag },
    {
      title: "样本数",
      key: "samples",
      render: (_value: unknown, row: TrainingRun) =>
        `${row.dataset_sample_count} (${row.train_sample_count}/${row.val_sample_count})`,
    },
    {
      title: "Accuracy",
      render: (_value: unknown, row: TrainingRun) => metricText(row.metrics_json?.level_accuracy),
    },
    {
      title: "Macro-F1",
      render: (_value: unknown, row: TrainingRun) => metricText(row.metrics_json?.macro_f1),
    },
    {
      title: "Detection",
      render: (_value: unknown, row: TrainingRun) => metricText(row.metrics_json?.detection_rate),
    },
  ];

  const versionColumns = [
    {
      title: "版本",
      key: "version",
      render: (_value: unknown, row: ModelVersion) => (
        <Space direction="vertical" size={0}>
          <Tooltip title={row.version_display_name}>
            <Typography.Text strong>{compactModelDisplayName(row.version_display_name)}</Typography.Text>
          </Tooltip>
          <Typography.Text type="secondary">{row.version_code}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "当前",
      key: "active",
      render: (_value: unknown, row: ModelVersion) =>
        row.is_active ? (
          <Tag color="green">当前</Tag>
        ) : (
          <Button
            size="small"
            onClick={() => activateMutation.mutate(row.id)}
            loading={activateMutation.isPending}
          >
            启用
          </Button>
        ),
    },
    {
      title: "来源任务",
      key: "sourceTask",
      render: (_value: unknown, row: ModelVersion) => (
        <Tooltip title={row.source_run_display_name ?? row.source_run_no ?? "-"}>
          <Button type="link" style={{ padding: 0 }} onClick={() => focusTrainingRun(row.training_run_id)}>
            {compactTaskDisplayName(row.source_run_display_name ?? row.source_run_no ?? "-")}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: "样本数",
      key: "samples",
      render: (_value: unknown, row: ModelVersion) =>
        `${row.dataset_sample_count} (${row.train_sample_count}/${row.val_sample_count})`,
    },
    {
      title: "Accuracy",
      render: (_value: unknown, row: ModelVersion) => metricText(row.level_accuracy),
    },
    {
      title: "Macro-F1",
      render: (_value: unknown, row: ModelVersion) => metricText(row.macro_f1),
    },
    {
      title: "Detection",
      render: (_value: unknown, row: ModelVersion) => metricText(row.detection_rate),
    },
    {
      title: "详情",
      key: "details",
      render: (_value: unknown, row: ModelVersion) => (
        <Button size="small" onClick={() => focusTrainingRun(row.training_run_id)}>
          查看任务
        </Button>
      ),
    },
  ];

  const predictionColumns = [
    { title: "任务", dataIndex: "run_no", ellipsis: true },
    { title: "状态", dataIndex: "status", render: statusTag },
    { title: "候选题数", dataIndex: "candidate_count" },
    { title: "选中题数", dataIndex: "selected_count" },
    { title: "进入待标注池", dataIndex: "moved_count" },
  ];

  const selectionBatchColumns = [
    {
      title: "批次",
      key: "batch_no",
      render: (_value: unknown, row: SelectionBatchSummary) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.batch_no}</Typography.Text>
          <Typography.Text type="secondary">
            {formatBatchType(row.algorithm_code)} · {formatDateTime(row.created_at)}
          </Typography.Text>
          {row.source_run_no ? (
            <Typography.Text type="secondary">来源任务：{row.source_run_no}</Typography.Text>
          ) : null}
        </Space>
      ),
    },
    {
      title: "策略",
      dataIndex: "algorithm_code",
      key: "algorithm_code",
      render: (value: string) => (
        <Tag color={coreSetAlgorithms.has(value as SelectionStrategy) ? "green" : "blue"}>
          {formatAlgorithmLabel(value)}
        </Tag>
      ),
    },
    {
      title: "选题结果",
      key: "counts",
      render: (_value: unknown, row: SelectionBatchSummary) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>
            候选 {row.candidate_count} / 选中 {row.selected_count} / 请求 {row.requested_count}
          </Typography.Text>
          <Typography.Text type="secondary">
            当前池中：未标注 {row.pending_count} · 待标注 {row.waiting_count} · 标注中 {row.in_progress_count}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_value: unknown, row: SelectionBatchSummary) => {
        const disabled = row.pending_count + row.waiting_count + row.in_progress_count <= 0;
        return (
          <Space wrap>
            <Button size="small" onClick={() => openQuestionSelection(row.question_ids)} disabled={row.question_ids.length <= 0}>
              查看题目
            </Button>
            <Popconfirm
              title="撤回本批次选题"
              description="会把本批次仍在标注中或待标注的题目回收到未标注池。"
              okText="确认撤回"
              cancelText="取消"
              disabled={disabled}
              onConfirm={() => void handleRollbackSelectionBatch(row.id)}
            >
              <Button size="small" disabled={disabled} loading={rollbackSelectionBatchMutation.isPending}>
                撤回本批次
              </Button>
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  const coresetRunColumns = [
    {
      title: "任务",
      key: "run_no",
      render: (_value: unknown, row: CoresetRun) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{row.run_no}</Typography.Text>
          {row.recommendation_batch_no ? (
            <Typography.Text type="secondary">
              结果批次：{row.recommendation_batch_no}
            </Typography.Text>
          ) : null}
          <Typography.Text type="secondary">{formatDateTime(row.created_at)}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "策略",
      key: "strategy",
      render: (_value: unknown, row: CoresetRun) => (
        <Space direction="vertical" size={0}>
          <Tag color="green">{formatAlgorithmLabel(row.strategy)}</Tag>
          <Typography.Text type="secondary">
            {row.update_mode === "incremental" ? "增量更新" : "全量选题"} ·{" "}
            {row.data_scope === "pending" ? "未标注池中的题目" : "全部题目"}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "状态",
      key: "status",
      render: (_value: unknown, row: CoresetRun) => (
        <Space direction="vertical" size={0}>
          <Tag color={getRunStatusColor(row.status)}>{getRunStatusLabel(row.status)}</Tag>
          <Typography.Text type="secondary">
            {String(row.metrics_json?.progress_label ?? row.metrics_json?.phase ?? "-")}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "结果",
      key: "result",
      render: (_value: unknown, row: CoresetRun) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>
            候选 {row.candidate_count} / 选中 {row.selected_count} / 进入待标注池 {row.moved_count}
          </Typography.Text>
          <Typography.Text type="secondary">
            模式：{String(row.metrics_json?.selection_mode ?? "-")}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_value: unknown, row: CoresetRun) => (
        <Space wrap>
          <Button size="small" onClick={() => setSelectedCoresetRun(row)}>
            查看详情
          </Button>
          <Button size="small" onClick={() => openQuestionSelection(row.question_ids)} disabled={row.question_ids.length <= 0}>
            查看题目
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          训练监控
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          查看主动学习训练任务、模型版本、预测任务，以及按相同参数分组后的指标趋势。题池治理与 CoreSet 历史任务统一保留在管理后台。
        </Typography.Paragraph>
      </Card>

      <Row id="training-summary" gutter={[16, 16]} className="page-section-anchor">
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard
            title="当前模型"
            value={compactModelDisplayName(data?.active_model?.version_display_name)}
            fullValue={data?.active_model?.version_display_name ?? "-"}
            hint="当前启用版本"
            loading={isLoading}
            ellipsisRows={2}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="训练样本" value={data?.completed_sample_count ?? 0} hint="可用于训练的已完成题目" loading={isLoading} />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="未标注候选" value={data?.pending_candidate_count ?? 0} hint="当前还未进入待标注池的题目" loading={isLoading} />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="模型版本数" value={modelVersions.length} hint="已登记到系统的模型版本" loading={isLoading} />
        </Col>
      </Row>

      <Card
        id="training-trends"
        className="page-section-anchor training-board-card"
        title="模型版本指标趋势"
        extra={(
          <Select
            style={{ minWidth: 420 }}
            placeholder="选择趋势分组"
            value={selectedTrendGroup?.key}
            options={trendGroups.map((item) => ({
              value: item.key,
              label: formatTrendGroupLabel(item),
            }))}
            onChange={setSelectedTrendGroupKey}
          />
        )}
      >
        {selectedTrendGroup ? (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Typography.Text type="secondary">
              {formatParameterSummary(selectedTrendGroup.parameter_summary)}
            </Typography.Text>
            <Typography.Text type="secondary">
              当前分组共 {selectedTrendGroup.point_count} 个趋势点。同参数、同数据集规模的重复训练会合并为一个点，只用于观察数据规模变化带来的趋势。
            </Typography.Text>
            <div ref={chartRef} style={{ width: "100%", height: 360 }} />
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可对比的趋势分组" />
        )}
      </Card>

      <div ref={trainingTableAnchorRef} />
      <Card id="training-runs" className="page-section-anchor training-board-card" title="训练任务">
        <Table<TrainingRun>
          rowKey="id"
          loading={isLoading}
          dataSource={trainingRuns}
          pagination={{
            pageSize: 6,
            showSizeChanger: true,
            pageSizeOptions: ["6", "10", "20"],
            showTotal: (total: number) => `共 ${total} 条训练任务`,
          }}
          expandable={{
            expandedRowKeys: expandedTrainingRunKeys,
            onExpandedRowsChange: (keys: readonly Key[]) => setExpandedTrainingRunKeys([...keys]),
            expandedRowRender: (row: TrainingRun) => <TrainingRunDetails row={row} />,
          }}
          columns={trainingColumns}
        />
      </Card>

      <Card id="training-models" className="page-section-anchor training-board-card" title="模型版本">
        <Table<ModelVersion>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={modelVersions}
          pagination={{
            pageSize: 8,
            showSizeChanger: true,
            pageSizeOptions: ["8", "10", "20"],
            showTotal: (total: number) => `共 ${total} 个模型版本`,
          }}
          columns={versionColumns}
        />
      </Card>

      <Card id="training-prediction-runs" className="page-section-anchor training-board-card" title="预测任务">
        <Table<PredictionRun>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={predictionRuns}
          pagination={{
            pageSize: 6,
            showSizeChanger: true,
            pageSizeOptions: ["6", "10", "20"],
            showTotal: (total: number) => `共 ${total} 个预测任务`,
          }}
          locale={{ emptyText: "暂无预测任务" }}
          columns={predictionColumns}
        />
      </Card>

      <Drawer
        title={selectedCoresetRun ? `CoreSet 任务详情 · ${selectedCoresetRun.run_no}` : "CoreSet 任务详情"}
        width={720}
        open={Boolean(selectedCoresetRun)}
        onClose={() => setSelectedCoresetRun(null)}
        destroyOnClose
      >
        {selectedCoresetRun ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="状态">
                <Tag color={getRunStatusColor(selectedCoresetRun.status)}>{getRunStatusLabel(selectedCoresetRun.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="运行阶段">
                {String(selectedCoresetRun.metrics_json?.progress_label ?? selectedCoresetRun.metrics_json?.phase ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="策略">{formatAlgorithmLabel(selectedCoresetRun.strategy)}</Descriptions.Item>
              <Descriptions.Item label="候选题目范围">
                {selectedCoresetRun.data_scope === "pending" ? "未标注池中的题目" : "全部题目"}
              </Descriptions.Item>
              <Descriptions.Item label="更新模式">
                {selectedCoresetRun.update_mode === "incremental" ? "增量更新" : "全量选题"}
              </Descriptions.Item>
              <Descriptions.Item label="基线批次">
                {selectedCoresetRun.baseline_batch_no ?? selectedCoresetRun.baseline_run_no ?? "-"}
              </Descriptions.Item>
              <Descriptions.Item label="请求数">{selectedCoresetRun.requested_count}</Descriptions.Item>
              <Descriptions.Item label="候选数">{selectedCoresetRun.candidate_count}</Descriptions.Item>
              <Descriptions.Item label="当前未标注池">
                {String(selectedCoresetRun.metrics_json?.current_pool_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="较基线新增">
                {String(selectedCoresetRun.metrics_json?.new_unlabeled_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="选中数">{selectedCoresetRun.selected_count}</Descriptions.Item>
              <Descriptions.Item label="进入待标注池数量">{selectedCoresetRun.moved_count}</Descriptions.Item>
              <Descriptions.Item label="运行模式">
                {String(selectedCoresetRun.metrics_json?.selection_mode ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="结果批次号">
                {selectedCoresetRun.recommendation_batch_no ?? selectedCoresetRun.batch_no ?? "-"}
              </Descriptions.Item>
              <Descriptions.Item label="历史锚点数">
                {String(selectedCoresetRun.metrics_json?.anchor_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="快照截止">
                {formatDateTime((selectedCoresetRun.metrics_json?.snapshot_created_before as string | null | undefined) ?? null)}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDateTime(selectedCoresetRun.created_at)}</Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {selectedCoresetRun.finished_at ? formatDateTime(selectedCoresetRun.finished_at) : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="分层簇数">
                {String(selectedCoresetRun.metrics_json?.cluster_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="有效簇数">
                {String(selectedCoresetRun.metrics_json?.nonempty_cluster_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="最大簇规模">
                {String(selectedCoresetRun.metrics_json?.largest_cluster_size ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="最小簇规模">
                {String(selectedCoresetRun.metrics_json?.smallest_cluster_size ?? "-")}
              </Descriptions.Item>
            </Descriptions>

            {selectedCoresetRun.error_message ? (
              <Card size="small">
                <Typography.Text type="danger">{selectedCoresetRun.error_message}</Typography.Text>
              </Card>
            ) : null}

            <Card size="small" title="运行指标">
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 12,
                }}
              >
                {JSON.stringify(selectedCoresetRun.metrics_json ?? {}, null, 2)}
              </pre>
            </Card>

            <Space wrap>
              <Button onClick={() => openQuestionSelection(selectedCoresetRun.question_ids)} disabled={selectedCoresetRun.question_ids.length <= 0}>
                查看本次选中题目
              </Button>
              <Button
                onClick={() => openQuestionSelection(selectedCoresetRun.moved_question_ids, "WAITING")}
                disabled={selectedCoresetRun.moved_question_ids.length <= 0}
              >
                查看本次进入待标注池的题目
              </Button>
            </Space>
          </Space>
        ) : null}
      </Drawer>
    </Space>
  );
}

function SummaryCard({
  title,
  value,
  fullValue,
  hint,
  loading,
  ellipsisRows = 1,
}: {
  title: string;
  value: string | number;
  fullValue?: string | number;
  hint?: string;
  loading?: boolean;
  ellipsisRows?: number;
}) {
  return (
    <Card className="training-summary-card training-board-card" bodyStyle={{ height: "100%", padding: 20 }}>
      <div className="training-summary-card__body">
        <Typography.Text type="secondary">{title}</Typography.Text>
        {loading ? (
          <Typography.Text type="secondary">加载中...</Typography.Text>
        ) : (
          <Tooltip title={String(fullValue ?? value)}>
            <Typography.Paragraph className="training-summary-card__value" ellipsis={{ rows: ellipsisRows }}>
              {String(value)}
            </Typography.Paragraph>
          </Tooltip>
        )}
        {hint ? <div className="training-summary-card__hint">{hint}</div> : null}
      </div>
    </Card>
  );
}

function TrainingRunDetails({ row }: { row: TrainingRun }) {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Descriptions
        bordered
        size="small"
        column={{ xs: 1, md: 2 }}
        items={[
          {
            key: "dataset",
            label: "数据集",
            children: `${row.dataset_sample_count} 条（训练 ${row.train_sample_count} / 验证 ${row.val_sample_count}）`,
          },
          {
            key: "linkedModel",
            label: "生成模型",
            children: row.related_model_display_name ? (
              <Tooltip title={row.related_model_display_name}>
                <Typography.Text>{compactModelDisplayName(row.related_model_display_name)}</Typography.Text>
              </Tooltip>
            ) : (
              "-"
            ),
          },
          {
            key: "modelType",
            label: "基础模型",
            children: `${row.model_type ?? "-"} / ${row.base_model_name ?? "-"}`,
          },
          {
            key: "group",
            label: "趋势分组",
            children: row.trend_group_key,
          },
          {
            key: "params",
            label: "参数设置",
            children: formatParameterSummary(row.parameter_summary),
            span: 2,
          },
          {
            key: "runNo",
            label: "任务编号",
            children: row.run_no,
            span: 2,
          },
        ]}
      />
      <EpochTable epochs={row.epochs} />
    </Space>
  );
}

function EpochTable({ epochs }: { epochs: TrainingEpoch[] }) {
  if (!epochs.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无 epoch 指标" />;
  }
  return (
    <Table<TrainingEpoch>
      rowKey="id"
      size="small"
      pagination={false}
      dataSource={epochs}
      columns={[
        { title: "Epoch", dataIndex: "epoch_no" },
        {
          title: "训练损失",
          render: (_value: unknown, row: TrainingEpoch) => metricText(row.train_loss),
        },
        {
          title: "验证损失",
          render: (_value: unknown, row: TrainingEpoch) => metricText(row.val_loss),
        },
        {
          title: "Accuracy",
          render: (_value: unknown, row: TrainingEpoch) => metricText(row.level_accuracy),
        },
        {
          title: "Macro-F1",
          render: (_value: unknown, row: TrainingEpoch) => metricText(row.macro_f1),
        },
        {
          title: "Detection",
          render: (_value: unknown, row: TrainingEpoch) => metricText(row.detection_rate),
        },
      ]}
    />
  );
}

function statusTag(status: string) {
  return <Tag color={getRunStatusColor(status)}>{getRunStatusLabel(status)}</Tag>;
}

function metricText(value?: number | null) {
  if (value === undefined || value === null) return "-";
  return value.toFixed(4);
}

function formatTrendGroupLabel(group: TrendGroup) {
  const parts = parseSummary(group.parameter_summary);
  const stage = stageText(parts.stage ?? group.target_stage ?? "-");
  const model = (parts.model ?? group.model_type ?? "-").toUpperCase();
  const sample = parts.samples ? `样本 ${parts.samples}` : "按样本规模观察";
  const batch = parts.batch ? `batch=${parts.batch}` : "";
  const lr = parts.lr ? `lr=${parts.lr}` : "";
  return [stage, model, sample, batch, lr].filter(Boolean).join(" | ");
}

function formatParameterSummary(summary: string) {
  const parts = parseSummary(summary);
  const mapping: Array<[string, string]> = [
    ["stage", "学段"],
    ["model", "模型类型"],
    ["base", "基础模型"],
    ["samples", "样本量"],
    ["epochs", "Epochs"],
    ["batch", "Batch Size"],
    ["lr", "学习率"],
    ["val", "验证集比例"],
    ["patience", "Patience"],
    ["max_len", "最大长度"],
    ["seed", "随机种子"],
    ["gold", "合并金标"],
    ["device", "训练设备"],
  ];
  return mapping
    .filter(([key]) => parts[key] !== undefined)
    .map(([key, label]) => {
      if (key === "stage") return `${label}：${stageText(parts[key] ?? "-")}`;
      if (key === "gold") return `${label}：${parts[key] === "yes" ? "是" : "否"}`;
      if (key === "device") return `${label}：${deviceText(parts[key] ?? "-")}`;
      if (key === "model") return `${label}：${String(parts[key] ?? "-").toUpperCase()}`;
      return `${label}：${parts[key] ?? "-"}`;
    })
    .join("，");
}

function parseSummary(summary: string) {
  return summary.split(", ").reduce<Record<string, string>>((acc, item) => {
    const [key, ...rest] = item.split("=");
    if (key) acc[key] = rest.join("=") || "";
    return acc;
  }, {});
}

function stageText(value: string) {
  if (value === "junior") return "初中";
  if (value === "senior") return "高中";
  return value;
}

function deviceText(value: string) {
  if (value === "cuda") return "GPU";
  if (value === "cpu") return "CPU";
  if (value === "auto") return "自动";
  return value;
}

function compactModelDisplayName(value?: string | null) {
  if (!value) return "-";
  const parts = value.split("-");
  const compactParts: string[] = [];
  const stage = parts[0];
  const model = parts[1];
  const sample = parts.find((item) => /^s\d+$/i.test(item));
  const epoch = parts.find((item) => /^e\d+$/i.test(item));
  const batch = parts.find((item) => /^b\d+$/i.test(item));
  const gold = parts.find((item) => /gold/i.test(item));

  if (stage) compactParts.push(stageText(stage));
  if (model) compactParts.push(model.toUpperCase());
  if (sample) compactParts.push(`${sample.replace(/^s/i, "")}题`);
  if (epoch) compactParts.push(epoch.toUpperCase());
  if (batch) compactParts.push(batch.toUpperCase());
  if (gold) compactParts.push(gold.toLowerCase() === "gold" ? "金标" : gold);

  if (!compactParts.length) return value;
  return compactParts.join(" / ");
}

function compactTaskDisplayName(value?: string | null) {
  if (!value) return "-";
  const parts = value.split("-");
  const stage = parts[0];
  const model = parts[1];
  const sample = parts.find((item) => /^s\d+$/i.test(item));

  if (!stage || !model || !sample) return value;
  return `${stageText(stage)} / ${model.toUpperCase()} / ${sample.replace(/^s/i, "")}题`;
}

function formatAlgorithmLabel(value: string) {
  const mapping: Record<string, string> = {
    moe: "MoE 融合策略",
    kmeans: "K-Means 覆盖",
    facility_location: "Facility Location",
    graph_cut: "Graph Cut",
    random: "随机抽样",
    mean_max_probability: "平均最高概率",
    min_max_probability: "最小最高概率",
    entropy: "信息熵",
    margin: "边际差值",
  };
  return mapping[value] ?? value;
}

function formatBatchType(value: string) {
  return coreSetAlgorithms.has(value as SelectionStrategy) ? "CoreSet 选题" : "低置信度选题";
}
