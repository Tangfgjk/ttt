import { Button, Card, Col, Descriptions, Empty, Row, Select, Space, Table, Tag, Tooltip, Typography } from "antd";
import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Key } from "react";

import {
  useActiveLearningOverview,
  useActivateModelVersion,
} from "@/modules/active-learning/hooks";
import type {
  ModelVersion,
  PredictionRun,
  TrainingEpoch,
  TrainingRun,
  TrendGroup,
} from "@/types/active-learning";

export function TrainingPage() {
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const trainingTableAnchorRef = useRef<HTMLDivElement | null>(null);
  const { data, isLoading } = useActiveLearningOverview();
  const activateMutation = useActivateModelVersion();
  const [selectedTrendGroupKey, setSelectedTrendGroupKey] = useState<string>();
  const [expandedTrainingRunKeys, setExpandedTrainingRunKeys] = useState<Key[]>([]);

  const trendGroups = data?.trend_groups ?? [];
  const trainingRuns = data?.training_runs ?? [];
  const modelVersions = data?.model_versions ?? [];

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
              {compactModelDisplayName(
                row.related_model_display_name ?? row.related_model_version_code,
              )}
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
    { title: "已入池", dataIndex: "moved_count" },
  ];

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          训练监控
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          查看主动学习训练任务、模型版本、预测任务以及按相同参数分组后的指标趋势。
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]} align="stretch">
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard
            title="当前模型"
            value={compactModelDisplayName(data?.active_model?.version_display_name)}
            fullValue={data?.active_model?.version_display_name ?? "-"}
            loading={isLoading}
            ellipsisRows={2}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="训练样本" value={data?.completed_sample_count ?? 0} loading={isLoading} />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="未标注候选" value={data?.pending_candidate_count ?? 0} loading={isLoading} />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <SummaryCard title="模型版本数" value={modelVersions.length} loading={isLoading} />
        </Col>
      </Row>

      <Card
        title="模型版本指标趋势"
        extra={
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
        }
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
      <Card title="训练任务">
        <Table<TrainingRun>
          rowKey="id"
          loading={isLoading}
          dataSource={trainingRuns}
          pagination={{
            pageSize: 6,
            showSizeChanger: false,
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

      <Card title="模型版本">
        <Table<ModelVersion>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={modelVersions}
          pagination={{
            pageSize: 8,
            showSizeChanger: false,
            showTotal: (total: number) => `共 ${total} 个模型版本`,
          }}
          columns={versionColumns}
        />
      </Card>

      <Card title="预测任务">
        <Table<PredictionRun>
          rowKey="id"
          size="small"
          loading={isLoading}
          dataSource={data?.prediction_runs ?? []}
          pagination={{
            pageSize: 6,
            showSizeChanger: false,
            showTotal: (total: number) => `共 ${total} 个预测任务`,
          }}
          locale={{ emptyText: "暂无预测任务" }}
          columns={predictionColumns}
        />
      </Card>
    </Space>
  );
}

function SummaryCard({
  title,
  value,
  fullValue,
  loading,
  ellipsisRows = 1,
}: {
  title: string;
  value: string | number;
  fullValue?: string | number;
  loading?: boolean;
  ellipsisRows?: number;
}) {
  return (
    <Card className="training-summary-card" bodyStyle={{ height: "100%", padding: 22 }}>
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
  const colors: Record<string, string> = {
    PENDING: "default",
    RUNNING: "blue",
    SUCCESS: "green",
    FAILED: "red",
  };
  const labels: Record<string, string> = {
    PENDING: "待执行",
    RUNNING: "运行中",
    SUCCESS: "成功",
    FAILED: "失败",
  };
  return <Tag color={colors[status] ?? "default"}>{labels[status] ?? status}</Tag>;
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
  if (sample) compactParts.push(sample.replace(/^s/i, "") + "题");
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
