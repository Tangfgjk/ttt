import { ReloadOutlined, SyncOutlined } from "@ant-design/icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
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

import { usePageHashScroll } from "@/app/use-page-hash-scroll";
import {
  annotationStatusOptions as sharedAnnotationStatusOptions,
  getAnnotationStatusLabel,
} from "@/constants/annotation-status";
import {
  getEmbeddingStatus,
  getQuestionDistribution,
  rebuildMissingEmbeddings,
} from "@/services/visualization";
import type { DistributionPoint, VisualizationMethod } from "@/types/visualization";

const statusColors: Record<string, string> = {
  PENDING: "#8c8c8c",
  WAITING: "#1677ff",
  IN_PROGRESS: "#fa8c16",
  REVIEW_PENDING: "#f5222d",
  COMPLETED: "#52c41a",
};

const statusOptions = [
  { label: "全部数据", value: "all" },
  ...sharedAnnotationStatusOptions
    .filter((item) => item.value)
    .map((item) => ({ label: item.label, value: item.value })),
];

const methodOptions: Array<{ label: string; value: VisualizationMethod }> = [
  { label: "PCA", value: "pca" },
  { label: "t-SNE", value: "tsne" },
  { label: "UMAP", value: "umap" },
];

const EMBEDDING_BATCH_LIMIT = 200;

export function VisualizationPage() {
  usePageHashScroll();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const chartRef = useRef<HTMLDivElement | null>(null);

  const [method, setMethod] = useState<VisualizationMethod>("pca");
  const [status, setStatus] = useState("all");
  const [selectedPoint, setSelectedPoint] = useState<DistributionPoint | null>(null);
  const [isCompletingAll, setIsCompletingAll] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["visualization", "embedding-status"],
    queryFn: getEmbeddingStatus,
    staleTime: 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const distributionQuery = useQuery({
    queryKey: ["visualization", "distribution", method, status],
    queryFn: () => getQuestionDistribution({ method, status }),
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
    placeholderData: (previousData) => previousData,
  });

  const handleCompleteAllEmbeddings = async () => {
    if (isCompletingAll) return;
    setIsCompletingAll(true);
    try {
      while (true) {
        const currentStatus = await getEmbeddingStatus();
        queryClient.setQueryData(["visualization", "embedding-status"], currentStatus);
        if (currentStatus.missing_embeddings <= 0) break;
        const result = await rebuildMissingEmbeddings(EMBEDDING_BATCH_LIMIT);
        if (result.created === 0) break;
      }
      await queryClient.invalidateQueries({ queryKey: ["visualization"] });
      message.success("题目嵌入补全完成");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "请检查后端依赖与模型路径";
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
      name: getAnnotationStatusLabel(itemStatus),
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
    const handleResize = () => chart.resize();
    window.addEventListener("resize", handleResize);
    chart.on("click", (params) => {
      const data = params.data as { point?: DistributionPoint } | undefined;
      if (data?.point) setSelectedPoint(data.point);
    });
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.dispose();
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.getInstanceByDom(chartRef.current);
    if (!chart) return;
    chart.setOption({
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: { data?: { point?: DistributionPoint } }) => {
          const point = params.data?.point;
          if (!point) return "";
          return [
            `题目 #${point.question_id}`,
            `状态：${getAnnotationStatusLabel(point.annotation_status)}`,
            `进度：${point.annotation_count}/${point.required_annotations}`,
            point.stem_preview,
          ].join("<br/>");
        },
      },
      legend: { top: 0, left: 0 },
      grid: { top: 48, left: 40, right: 20, bottom: 50 },
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

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card id="visualization-status" className="page-section-anchor">
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Space wrap align="center" style={{ justifyContent: "space-between", width: "100%" }}>
            <div>
              <Typography.Title level={3} style={{ marginTop: 0, marginBottom: 4 }}>
                嵌入可视化
              </Typography.Title>
              <Typography.Text type="secondary">
                基于题目嵌入矩阵查看题库分布，聚焦选题覆盖和空间邻近关系。
              </Typography.Text>
            </div>
            <Space wrap>
              <Select style={{ width: 150 }} value={status} options={statusOptions} onChange={setStatus} />
              <Select style={{ width: 120 }} value={method} options={methodOptions} onChange={setMethod} />
              <Button icon={<ReloadOutlined />} loading={distributionQuery.isFetching} onClick={() => distributionQuery.refetch()}>
                刷新图表
              </Button>
              <Button icon={<SyncOutlined spin={isCompletingAll} />} loading={isCompletingAll} onClick={() => void handleCompleteAllEmbeddings()}>
                一键补全嵌入
              </Button>
            </Space>
          </Space>

          {statusQuery.data && !statusQuery.data.model_available ? (
            <Alert
              type="warning"
              showIcon
              message="嵌入模型暂不可用"
              description={`请确认后端已安装 torch/transformers，且模型路径存在：${statusQuery.data.model_path}`}
            />
          ) : null}
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={6}><Card><Statistic title="总试题" value={statusQuery.data?.total_questions ?? 0} loading={statusQuery.isLoading} /></Card></Col>
        <Col xs={24} md={6}><Card><Statistic title="已有嵌入" value={statusQuery.data?.embedded_questions ?? 0} loading={statusQuery.isLoading} /></Card></Col>
        <Col xs={24} md={6}><Card><Statistic title="当前绘制" value={distributionQuery.data?.embedding_count ?? 0} loading={distributionQuery.isLoading} /></Card></Col>
        <Col xs={24} md={6}><Card><Statistic title="缺失嵌入" value={statusQuery.data?.missing_embeddings ?? 0} loading={statusQuery.isLoading} /></Card></Col>
      </Row>

      <Card id="visualization-chart" className="page-section-anchor">
        <div ref={chartRef} style={{ width: "100%", height: 560 }} />
        {!distributionQuery.data?.points.length ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={distributionQuery.isLoading ? "正在加载分布数据" : "暂无可视化点位，请先补全题目嵌入"} style={{ marginTop: -360, marginBottom: 220 }} />
        ) : null}
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card title="状态统计">
            <Space wrap>
              {Object.entries(statusColors).map(([key, color]) => (
                <Tag key={key} color={color}>{getAnnotationStatusLabel(key)} {summary[key] ?? 0}</Tag>
              ))}
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={14} id="visualization-detail" className="page-section-anchor">
          <Card title="选中试题详情">
            {selectedPoint ? (
              <>
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="题目 ID">#{selectedPoint.question_id}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={statusColors[selectedPoint.annotation_status]}>
                      {getAnnotationStatusLabel(selectedPoint.annotation_status)}
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
                  <Button type="primary" onClick={() => navigate(`/questions?question_id=${selectedPoint.question_id}`)}>
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
