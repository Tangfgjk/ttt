import { ReloadOutlined, SyncOutlined } from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Tag,
  Typography,
  message,
} from "antd";
import * as echarts from "echarts";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getEmbeddingStatus,
  getQuestionDistribution,
  rebuildMissingEmbeddings,
} from "@/services/visualization";
import type { DistributionPoint, VisualizationMethod } from "@/types/visualization";

const statusLabels: Record<string, string> = {
  PENDING: "未标注",
  WAITING: "待标注",
  IN_PROGRESS: "标注中",
  REVIEW_PENDING: "待复核",
  COMPLETED: "已完成",
};

const statusColors: Record<string, string> = {
  PENDING: "#8c8c8c",
  WAITING: "#1677ff",
  IN_PROGRESS: "#fa8c16",
  REVIEW_PENDING: "#f5222d",
  COMPLETED: "#52c41a",
};

const statusOptions = [
  { label: "全部数据", value: "all" },
  { label: "未标注", value: "PENDING" },
  { label: "待标注", value: "WAITING" },
  { label: "标注中", value: "IN_PROGRESS" },
  { label: "待复核", value: "REVIEW_PENDING" },
  { label: "已完成", value: "COMPLETED" },
];

const methodOptions: Array<{ label: string; value: VisualizationMethod }> = [
  { label: "PCA", value: "pca" },
  { label: "t-SNE", value: "tsne" },
  { label: "UMAP", value: "umap" },
];

const EMBEDDING_BATCH_LIMIT = 200;

export function VisualizationPage() {
  const navigate = useNavigate();
  const chartRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);
  const queryClient = useQueryClient();
  const [method, setMethod] = useState<VisualizationMethod>("pca");
  const [status, setStatus] = useState("all");
  const [selectedPoint, setSelectedPoint] = useState<DistributionPoint | null>(null);
  const [isCompletingAll, setIsCompletingAll] = useState(false);
  const [completionStats, setCompletionStats] = useState({
    created: 0,
    failed: 0,
    batches: 0,
  });

  const statusQuery = useQuery({
    queryKey: ["visualization", "embedding-status"],
    queryFn: getEmbeddingStatus,
    staleTime: 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const distributionQuery = useQuery({
    queryKey: ["visualization", "distribution", method, status],
    queryFn: () => getQuestionDistribution({ method, status }),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    placeholderData: (previousData) => previousData,
  });

  const handleCompleteAllEmbeddings = async () => {
    if (isCompletingAll) return;
    setIsCompletingAll(true);
    setCompletionStats({ created: 0, failed: 0, batches: 0 });

    let totalCreated = 0;
    let totalFailed = 0;
    let batches = 0;

    try {
      while (true) {
        const currentStatus = await getEmbeddingStatus();
        queryClient.setQueryData(["visualization", "embedding-status"], currentStatus);
        if (currentStatus.missing_embeddings <= 0) break;

        const result = await rebuildMissingEmbeddings(EMBEDDING_BATCH_LIMIT);
        batches += 1;
        totalCreated += result.created;
        totalFailed += result.failed;
        setCompletionStats({
          created: totalCreated,
          failed: totalFailed,
          batches,
        });
        const nextStatus = await getEmbeddingStatus();
        queryClient.setQueryData(["visualization", "embedding-status"], nextStatus);

        if (result.created === 0) break;
      }

      await queryClient.invalidateQueries({ queryKey: ["visualization"] });
      message.success(`一键补全完成，新增 ${totalCreated} 条嵌入`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : "请检查后端 Roberta 依赖和模型路径";
      message.error(`一键补全中断：${detail}`);
    } finally {
      setIsCompletingAll(false);
    }
  };

  const groupedSeries = useMemo(() => {
    const points = distributionQuery.data?.points ?? [];
    return Object.entries(
      points.reduce<Record<string, DistributionPoint[]>>((groups, point) => {
        groups[point.annotation_status] = groups[point.annotation_status] ?? [];
        groups[point.annotation_status].push(point);
        return groups;
      }, {}),
    ).map(([itemStatus, pointsForStatus]) => ({
      name: statusLabels[itemStatus] ?? itemStatus,
      type: "scatter",
      symbolSize: 7,
      progressive: 4000,
      progressiveThreshold: 8000,
      itemStyle: { color: statusColors[itemStatus] ?? "#595959", opacity: 0.78 },
      emphasis: { focus: "series" },
      data: pointsForStatus.map((point) => ({
        value: [point.x, point.y],
        point,
      })),
    }));
  }, [distributionQuery.data?.points]);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    chartInstanceRef.current = chart;
    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    chart.on("click", (params) => {
      const data = params.data as { point?: DistributionPoint } | undefined;
      if (data?.point) setSelectedPoint(data.point);
    });
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
      animation: false,
      animationThreshold: 5000,
      tooltip: {
        trigger: "item",
        formatter: (params: { data?: { point?: DistributionPoint } }) => {
          const point = params.data?.point;
          if (!point) return "";
          return [
            `题目 #${point.question_id}`,
            `状态：${statusLabels[point.annotation_status] ?? point.annotation_status}`,
            `进度：${point.annotation_count}/${point.required_annotations}`,
            point.stem_preview,
          ].join("<br/>");
        },
      },
      legend: {
        top: 0,
        left: 0,
      },
      grid: {
        top: 48,
        left: 40,
        right: 20,
        bottom: 50,
      },
      xAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: "#f0f0f0" } } },
      yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: "#f0f0f0" } } },
      dataZoom: [
        { type: "inside", xAxisIndex: 0 },
        { type: "inside", yAxisIndex: 0 },
        { type: "slider", xAxisIndex: 0, height: 18, bottom: 16 },
      ],
      series: groupedSeries,
    });
    chart.resize();
  }, [groupedSeries]);

  const summary = distributionQuery.data?.summary ?? {};
  const embeddingStatus = statusQuery.data;
  const completionPercent = embeddingStatus?.total_questions
    ? Number(((embeddingStatus.embedded_questions / embeddingStatus.total_questions) * 100).toFixed(2))
    : 0;

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Space wrap align="center" style={{ justifyContent: "space-between", width: "100%" }}>
            <div>
              <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
                试题嵌入可视化
              </Typography.Title>
              <Typography.Text type="secondary">
                基于 Roberta 题目嵌入矩阵，将题库降维到二维空间查看分布和标注状态。
              </Typography.Text>
            </div>
            <Space wrap>
              <Select
                style={{ width: 150 }}
                value={status}
                options={statusOptions}
                onChange={setStatus}
              />
              <Select
                style={{ width: 120 }}
                value={method}
                options={methodOptions}
                onChange={setMethod}
              />
              <Button
                icon={<ReloadOutlined />}
                loading={distributionQuery.isFetching}
                onClick={() => distributionQuery.refetch()}
              >
                刷新图表
              </Button>
              <Button
                icon={<SyncOutlined spin={isCompletingAll} />}
                loading={isCompletingAll}
                onClick={handleCompleteAllEmbeddings}
              >
                一键补全嵌入
              </Button>
            </Space>
          </Space>

          {statusQuery.data && !statusQuery.data.model_available ? (
            <Alert
              type="warning"
              showIcon
              message="Roberta 模型暂不可用"
              description={`请确认后端已安装 torch/transformers，且模型路径存在：${statusQuery.data.model_path}`}
            />
          ) : null}

          {isCompletingAll ? (
            <Alert
              type="info"
              showIcon
              message="正在一键补全题目嵌入"
              description={
                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                  <Progress percent={completionPercent} />
                  <Typography.Text type="secondary">
                    已完成 {embeddingStatus?.embedded_questions ?? 0}/
                    {embeddingStatus?.total_questions ?? 0}，本次新增 {completionStats.created}
                    条，失败 {completionStats.failed} 条，已处理 {completionStats.batches} 批。
                  </Typography.Text>
                </Space>
              }
            />
          ) : null}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="总试题" value={statusQuery.data?.total_questions ?? 0} loading={statusQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="已有嵌入" value={statusQuery.data?.embedded_questions ?? 0} loading={statusQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="当前绘制" value={distributionQuery.data?.embedding_count ?? 0} loading={distributionQuery.isLoading} />
          </Card>
        </Col>
        <Col xs={24} md={6}>
          <Card>
            <Statistic title="缺失嵌入" value={statusQuery.data?.missing_embeddings ?? 0} loading={statusQuery.isLoading} />
          </Card>
        </Col>
      </Row>

      <Card>
        <div ref={chartRef} style={{ width: "100%", height: 560 }} />
        {!distributionQuery.data?.points.length ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={distributionQuery.isLoading ? "正在加载分布数据" : "暂无可视化点位，请先补全题目嵌入"}
            style={{ marginTop: -360, marginBottom: 220 }}
          />
        ) : null}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card title="状态统计">
            <Space wrap>
              {Object.entries(statusLabels).map(([key, label]) => (
                <Tag key={key} color={statusColors[key]}>
                  {label} {summary[key] ?? 0}
                </Tag>
              ))}
            </Space>
            <Typography.Paragraph type="secondary" style={{ marginTop: 16, marginBottom: 0 }}>
              当前降维方法：{distributionQuery.data?.method ?? method}
              {distributionQuery.data?.method !== distributionQuery.data?.requested_method
                ? `，已从 ${distributionQuery.data?.requested_method} 自动回退`
                : ""}
            </Typography.Paragraph>
          </Card>
        </Col>
        <Col xs={24} lg={14}>
          <Card title="选中试题详情">
            {selectedPoint ? (
              <>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="题目 ID">#{selectedPoint.question_id}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Tag color={statusColors[selectedPoint.annotation_status]}>
                    {statusLabels[selectedPoint.annotation_status] ?? selectedPoint.annotation_status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="标注进度">
                  {selectedPoint.annotation_count}/{selectedPoint.required_annotations}
                </Descriptions.Item>
                <Descriptions.Item label="坐标">
                  ({selectedPoint.x}, {selectedPoint.y})
                </Descriptions.Item>
                <Descriptions.Item label="题干摘要" span={2}>
                  {selectedPoint.stem_preview}
                </Descriptions.Item>
              </Descriptions>
              <div style={{ marginTop: 16 }}>
                <Button
                  type="primary"
                  onClick={() => navigate(`/questions?question_id=${selectedPoint.question_id}`)}
                >
                  跳转到统一题池查看详情
                </Button>
              </div>
              </>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="点击散点查看题目详情" />
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
