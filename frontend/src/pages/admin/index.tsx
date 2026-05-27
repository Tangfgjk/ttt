import {
  ClusterOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Form,
  InputNumber,
  Popconfirm,
  Progress,
  Row,
  Select,
  Segmented,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
  message,
  theme,
} from "antd";
import type { AxiosError } from "axios";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";

import { formatBackendDateTime as formatDateTime } from "@/app/date-time";
import { usePageHashScroll } from "@/app/use-page-hash-scroll";
import { useAuthStore } from "@/app/store/auth-store";
import {
  annotationStatusColorMap,
  annotationStatusLabelMap,
} from "@/constants/annotation-status";
import { getRunStatusColor, getRunStatusLabel } from "@/constants/run-status";
import {
  useActiveLearningOverview,
  useCancelCoresetRun,
  useCancelPredictionRun,
  useCancelTrainingRun,
  useStartCoresetRun,
  useStartPredictionRun,
  useStartTrainingRun,
  useTrainingRunLogs,
} from "@/modules/active-learning/hooks";
import {
  useAnnotationPolicy,
  useAnnotationPoolSummary,
  useResetAnnotationPools,
  useRollbackSelectionBatch,
  useSelectionBatches,
  useSelectionStrategies,
  useUpdateAnnotationPolicy,
} from "@/modules/annotations/hooks";
import type {
  ActiveLearningStage,
  ConfidenceStrategy,
  CoresetRun,
  CoresetUpdateMode,
  PredictionRun,
  TrainingRun,
} from "@/types/active-learning";
import type {
  AnnotatorCount,
  AnnotationPolicySyncStatus,
  AnnotationPoolStatus,
  SelectionBatchSummary,
  SelectionDataScope,
  SelectionStrategy,
} from "@/types/annotations";

const TRAINING_INCLUDE_GOLD_STORAGE_KEY = "admin.training.include_gold_labels";

const poolStatusItems: Array<{
  status: AnnotationPoolStatus;
  label: string;
  color: string;
}> = [
  { status: "PENDING", label: `${annotationStatusLabelMap.PENDING}池`, color: annotationStatusColorMap.PENDING },
  { status: "WAITING", label: `${annotationStatusLabelMap.WAITING}池`, color: annotationStatusColorMap.WAITING },
  { status: "IN_PROGRESS", label: `${annotationStatusLabelMap.IN_PROGRESS}池`, color: annotationStatusColorMap.IN_PROGRESS },
  { status: "REVIEW_PENDING", label: `${annotationStatusLabelMap.REVIEW_PENDING}池`, color: annotationStatusColorMap.REVIEW_PENDING },
  { status: "COMPLETED", label: `${annotationStatusLabelMap.COMPLETED}池`, color: annotationStatusColorMap.COMPLETED },
];

const coreSetAlgorithms = new Set<SelectionStrategy>([
  "moe",
  "kmeans",
  "facility_location",
  "graph_cut",
  "random",
]);

type ProgressStatus = "normal" | "active" | "success" | "exception";

type ProgressInfo = {
  percent: number;
  status: ProgressStatus;
  text: string;
  detail: string;
};

function readStoredIncludeGoldLabels() {
  const stored = window.localStorage.getItem(TRAINING_INCLUDE_GOLD_STORAGE_KEY);
  if (stored === null) return true;
  return stored === "true";
}

export function AdminPage() {
  usePageHashScroll();

  const navigate = useNavigate();
  const { token } = theme.useToken();
  const session = useAuthStore((state) => state.session);
  const [trainingForm] = Form.useForm();
  const [predictionForm] = Form.useForm();
  const [coresetForm] = Form.useForm();
  const [includeGoldLabels, setIncludeGoldLabels] = useState(
    readStoredIncludeGoldLabels,
  );
  const [selectedCoresetRun, setSelectedCoresetRun] = useState<CoresetRun | null>(
    null,
  );
  const trainingCardRef = useRef<HTMLDivElement | null>(null);
  const predictionCardRef = useRef<HTMLDivElement | null>(null);
  const [trainingCardHeight, setTrainingCardHeight] = useState<number | undefined>();

  const { data: activeLearning } = useActiveLearningOverview();
  const { data: annotationPolicy } = useAnnotationPolicy();
  const {
    data: poolSummary,
    isLoading: isPoolSummaryLoading,
    refetch: refetchPoolSummary,
  } = useAnnotationPoolSummary();
  const { data: selectionStrategies = [] } = useSelectionStrategies();
  const { data: selectionBatches = [] } = useSelectionBatches();

  const trainingMutation = useStartTrainingRun();
  const cancelTrainingMutation = useCancelTrainingRun();
  const predictionMutation = useStartPredictionRun();
  const cancelPredictionMutation = useCancelPredictionRun();
  const coresetMutation = useStartCoresetRun();
  const cancelCoresetMutation = useCancelCoresetRun();
  const resetPoolsMutation = useResetAnnotationPools();
  const rollbackSelectionBatchMutation = useRollbackSelectionBatch();
  const updateAnnotationPolicyMutation = useUpdateAnnotationPolicy();

  const latestTrainingRun = latestRun(activeLearning?.training_runs);
  const latestPredictionRun = latestRun(activeLearning?.prediction_runs);
  const latestCoresetRun = latestRun(activeLearning?.coreset_runs);
  const latestCoreSetResult =
    latestCoresetRun?.status === "SUCCESS" ? latestCoresetRun : null;

  const isTrainingActive = ["PENDING", "RUNNING"].includes(
    latestTrainingRun?.status ?? "",
  );
  const isPredictionActive = ["PENDING", "RUNNING"].includes(
    latestPredictionRun?.status ?? "",
  );
  const isCoresetActive = ["PENDING", "RUNNING"].includes(
    latestCoresetRun?.status ?? "",
  );

  const minimumTrainingSamples =
    Form.useWatch("min_train_samples", trainingForm) ?? 5;
  const coresetStrategy = Form.useWatch("strategy", coresetForm) ?? "kmeans";
  const coresetDataScope = Form.useWatch("data_scope", coresetForm) ?? "pending";
  const incrementalSummary =
    activeLearning?.coreset_incremental_by_strategy?.[coresetStrategy] ??
    activeLearning?.coreset_incremental ??
    null;
  const canRunIncrementalForSelectedStrategy =
    Boolean(incrementalSummary?.can_run_incremental) &&
    incrementalSummary?.baseline_strategy === coresetStrategy;
  const hasNewUnlabeledSinceBaseline =
    canRunIncrementalForSelectedStrategy &&
    (incrementalSummary?.new_unlabeled_count ?? 0) > 0;
  const { data: latestTrainingLog } = useTrainingRunLogs(
    latestTrainingRun?.id,
    Boolean(latestTrainingRun),
  );

  const updateTrainingCardHeight = useCallback(() => {
    const trainingCard = trainingCardRef.current;
    const predictionCard = predictionCardRef.current;
    if (!trainingCard || !predictionCard) return;

    if (!window.matchMedia("(min-width: 1200px)").matches) {
      setTrainingCardHeight(undefined);
      return;
    }

    const trainingTop = trainingCard.getBoundingClientRect().top;
    const predictionBottom = predictionCard.getBoundingClientRect().bottom;
    const nextHeight = Math.max(420, Math.round(predictionBottom - trainingTop));
    setTrainingCardHeight((previous) =>
      previous === undefined || Math.abs(previous - nextHeight) > 1
        ? nextHeight
        : previous,
    );
  }, []);

  useLayoutEffect(() => {
    updateTrainingCardHeight();

    const resizeObserver = new ResizeObserver(updateTrainingCardHeight);
    if (predictionCardRef.current) {
      resizeObserver.observe(predictionCardRef.current);
    }
    window.addEventListener("resize", updateTrainingCardHeight);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateTrainingCardHeight);
    };
  }, [activeLearning, latestTrainingLog, updateTrainingCardHeight]);

  const versionOptions = (activeLearning?.model_versions ?? []).map((item) => ({
    value: item.id,
    label: item.is_active
      ? `${item.version_display_name}（当前）`
      : item.version_display_name,
  }));

  const strategyOptions = selectionStrategies.map((item) => ({
    value: item.code,
    label: item.name,
  }));

  const poolCounts = poolStatusItems.map((item) => ({
    ...item,
    count:
      poolSummary?.items.find((summaryItem) => summaryItem.status === item.status)
        ?.count ?? 0,
  }));

  const currentAnnotatorCount = annotationPolicy?.annotator_count ?? 3;
  const policySyncStatus = annotationPolicy?.sync_status;

  useEffect(() => {
    trainingForm.setFieldValue("include_gold_labels", includeGoldLabels);
  }, [includeGoldLabels, trainingForm]);

  useEffect(() => {
    void refetchPoolSummary();
  }, [
    latestPredictionRun?.status,
    latestPredictionRun?.moved_count,
    latestCoresetRun?.recommendation_batch_id,
    refetchPoolSummary,
  ]);

  const trainingProgress = getTrainingProgress(latestTrainingRun);
  const predictionProgress = getPredictionProgress(latestPredictionRun);
  const coresetProgress = getCoreSetProgress(latestCoresetRun);

  const getRequestErrorMessage = (error: unknown, fallback: string) => {
    const axiosError = error as AxiosError<{ detail?: string }>;
    if (axiosError.response?.data?.detail) {
      return axiosError.response.data.detail;
    }
    if (axiosError.code === "ECONNABORTED") {
      return `${fallback}：请求超时，请稍后重试。`;
    }
    if (axiosError.message) {
      return `${fallback}：${axiosError.message}`;
    }
    return fallback;
  };

  const handleStartTraining = async (values: {
    target_stage: ActiveLearningStage;
    epochs: number;
    batch_size: number;
    learning_rate: number;
    val_size: number;
    patience: number;
    max_length: number;
    min_train_samples: number;
    device: "auto" | "cpu" | "cuda";
  }) => {
    const result = await trainingMutation.mutateAsync({
      ...values,
      random_seed: 42,
      include_gold_labels: includeGoldLabels,
      triggered_by_user_id: session?.id ?? null,
    });
    message.success(`训练任务已创建：${result.run_no}`);
  };

  const handleCancelTraining = async () => {
    if (!latestTrainingRun || !isTrainingActive) return;
    const result = await cancelTrainingMutation.mutateAsync(latestTrainingRun.id);
    message.success(`训练任务已结束：${result.run_no}`);
  };

  const handleStartPrediction = async (values: {
    model_version_id?: number | null;
    select_count: number;
    confidence_strategy: ConfidenceStrategy;
    batch_size: number;
    auto_move_to_waiting: boolean;
  }) => {
    const result = await predictionMutation.mutateAsync({
      ...values,
      target_stage: "junior",
      model_version_id: values.model_version_id ?? null,
      triggered_by_user_id: session?.id ?? null,
    });
    message.success(`预测任务已创建：${result.run_no}`);
  };

  const handleCancelPrediction = async () => {
    if (!latestPredictionRun || !isPredictionActive) return;
    const result = await cancelPredictionMutation.mutateAsync(
      latestPredictionRun.id,
    );
    message.success(`预测任务已结束：${result.run_no}`);
  };

  const handleCoreSetSelection = async (values: {
    strategy: SelectionStrategy;
    count: number;
    data_scope: SelectionDataScope;
    update_mode: CoresetUpdateMode;
  }) => {
    try {
      const result = await coresetMutation.mutateAsync({
        ...values,
        triggered_by_user_id: session?.id ?? null,
      });
      message.success(`CoreSet 任务已创建：${result.run_no}`);
    } catch (error) {
      message.error(getRequestErrorMessage(error, "CoreSet 选题失败"));
    }
  };

  const handleStartIncrementalCoreSet = async () => {
    const values = await coresetForm.validateFields();
    await handleCoreSetSelection({
      strategy: values.strategy as SelectionStrategy,
      count: Number(values.count),
      data_scope: values.data_scope as SelectionDataScope,
      update_mode: "incremental",
    });
  };

  const handleCancelCoreset = async () => {
    if (!latestCoresetRun || !isCoresetActive) return;
    const result = await cancelCoresetMutation.mutateAsync(latestCoresetRun.id);
    message.success(`CoreSet 任务已结束：${result.run_no}`);
  };

  const handleResetPools = async () => {
    if (!session) return;
    const result = await resetPoolsMutation.mutateAsync({
      admin_user_id: session.id,
    });
    message.success(
      `题池已回收：回收标注中 ${result.recalled_in_progress_count} 题，回收待标注 ${result.returned_waiting_count} 题。`,
    );
  };

  const handleRollbackSelectionBatch = async (batchId: number) => {
    if (!session) return;
    const result = await rollbackSelectionBatchMutation.mutateAsync({
      batchId,
      payload: { admin_user_id: session.id },
    });
    message.success(
      `已撤回批次 ${result.batch_no}：回收标注中 ${result.recalled_in_progress_count} 题，退回待标注 ${result.returned_waiting_count} 题。`,
    );
  };

  const scrollToSection = (sectionId: string) => {
    const target = document.getElementById(sectionId);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    window.history.replaceState(null, "", `#${sectionId}`);
  };

  const handleAnnotatorCountChange = async (value: string | number) => {
    if (!session) return;
    const annotatorCount = Number(value) as AnnotatorCount;
    try {
      const result = await updateAnnotationPolicyMutation.mutateAsync({
        admin_user_id: session.id,
        annotator_count: annotatorCount,
      });
      message.success(
        `已切换为 ${result.annotator_count} 人标注策略，${result.affected_question_count} 道未开工题目正在后台同步。`,
      );
    } catch (error) {
      message.error(getRequestErrorMessage(error, "更新标注策略失败"));
    }
  };

  const openQuestionSelection = (
    questionIds: number[],
    annotationStatus?: string,
  ) => {
    if (!questionIds.length) {
      message.info("当前没有可查看的题目。");
      return;
    }
    const params = new URLSearchParams();
    params.set("question_ids", questionIds.join(","));
    if (annotationStatus) {
      params.set("annotation_status", annotationStatus);
    }
    navigate(`/questions?${params.toString()}`);
  };

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
            当前池中：未标注 {row.pending_count} · 待标注 {row.waiting_count} · 标注中{" "}
            {row.in_progress_count}
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "操作",
      key: "actions",
      render: (_value: unknown, row: SelectionBatchSummary) => {
        const disabled =
          row.pending_count + row.waiting_count + row.in_progress_count <= 0;
        return (
          <Space wrap>
            <Button
              size="small"
              onClick={() => openQuestionSelection(row.question_ids)}
              disabled={row.question_ids.length <= 0}
            >
              查看题目
            </Button>
            <Popconfirm
              title="撤回本次选题"
              description="会把本批次仍在标注中或待标注的题目回收到未标注池。"
              okText="确认撤回"
              cancelText="取消"
              disabled={disabled}
              onConfirm={() => void handleRollbackSelectionBatch(row.id)}
            >
              <Button
                size="small"
                disabled={disabled}
                loading={rollbackSelectionBatchMutation.isPending}
              >
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
          <Typography.Text type="secondary">
            {formatDateTime(row.created_at)}
          </Typography.Text>
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
          <Button
            size="small"
            onClick={() => openQuestionSelection(row.question_ids)}
            disabled={row.question_ids.length <= 0}
          >
            查看题目
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" size={18} style={{ width: "100%" }}>
      <Card
        style={{
          border: `1px solid ${token.colorBorderSecondary}`,
          boxShadow: token.boxShadowTertiary,
        }}
      >
        <Row align="middle" justify="space-between" gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Space direction="vertical" size={4}>
              <Typography.Title level={3} style={{ margin: 0 }}>
                管理后台
              </Typography.Title>
              <Typography.Text type="secondary">
                主动学习闭环操作台：训练模型、低置信度选题、CoreSet 选题，以及题池治理、批次撤回与状态回收。
              </Typography.Text>
            </Space>
          </Col>
          <Col xs={24} lg={8}>
            <Space
              size={8}
              wrap
              style={{ justifyContent: "flex-end", width: "100%" }}
            >
              <Tag color={activeLearning?.active_model ? "green" : "default"}>
                当前模型：{activeLearning?.active_model?.version_display_name ?? "暂无模型"}
              </Tag>
              <Tag color="blue">版本数：{activeLearning?.model_versions.length ?? 0}</Tag>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card
        size="small"
        style={{ boxShadow: token.boxShadowTertiary }}
        bodyStyle={{ paddingBlock: 12 }}
      >
        <Space size={[8, 8]} wrap>
          {[
            { id: "admin-policy", label: "标注策略" },
            { id: "admin-training", label: "训练模型" },
            { id: "admin-pools", label: "题池治理" },
            { id: "admin-coreset-history", label: "CoreSet 历史任务" },
            { id: "admin-prediction", label: "低置信度预测" },
            { id: "admin-coreset", label: "CoreSet 选题" },
          ].map((item) => (
            <Button key={item.id} onClick={() => scrollToSection(item.id)}>
              {item.label}
            </Button>
          ))}
        </Space>
      </Card>

      <Card
        id="admin-policy"
        className="page-section-anchor"
        title="标注策略控制台"
        extra={
          <Tag
            color={
              currentAnnotatorCount === 1
                ? "green"
                : currentAnnotatorCount === 2
                  ? "blue"
                  : "purple"
            }
          >
            {currentAnnotatorCount} 人模式
          </Tag>
        }
        style={{ boxShadow: token.boxShadowTertiary }}
      >
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Alert
            type="info"
            showIcon
            message={
              annotationPolicy?.strategy_description ??
              "三人独立标注，按多数聚合；存在争议时进入复核。"
            }
            description="该配置会用于后续进入待标注池的题目，并同步到当前尚未开始的待标注题和未标注题。"
          />
          {policySyncStatus ? (
            <Alert
              showIcon
              type={annotationPolicySyncAlertType(policySyncStatus.status)}
              message={annotationPolicySyncMessage(policySyncStatus)}
              description={annotationPolicySyncDescription(policySyncStatus)}
            />
          ) : null}
          <Row gutter={[16, 16]} align="middle">
            <Col xs={24} lg={14}>
              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                <Typography.Text strong>标注人数</Typography.Text>
                <Segmented
                  block
                  options={[
                    { label: "1 人", value: 1 },
                    { label: "2 人", value: 2 },
                    { label: "3 人", value: 3 },
                  ]}
                  value={currentAnnotatorCount}
                  onChange={(value: string | number) =>
                    void handleAnnotatorCountChange(value)
                  }
                  disabled={updateAnnotationPolicyMutation.isPending}
                />
              </Space>
            </Col>
            <Col xs={24} lg={10}>
              <Space direction="vertical" size={6}>
                <Typography.Text>当前要求人数：{currentAnnotatorCount}</Typography.Text>
                <Typography.Text type="secondary">
                  {currentAnnotatorCount === 1
                    ? "标注员提交后直接形成最终结果，不创建复核任务。"
                    : currentAnnotatorCount === 2
                      ? "两位标注员一致则自动完成；不一致时进入复核队列。"
                      : "三位标注员提交后按多数聚合；无法收敛的维度进入复核。"}
                </Typography.Text>
              </Space>
            </Col>
          </Row>
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        {poolCounts.map((item) => (
          <Col xs={24} sm={12} lg={8} xl={4} key={item.status}>
            <Card
              size="small"
              hoverable
              loading={isPoolSummaryLoading}
              onClick={() => navigate(`/questions?annotation_status=${item.status}`)}
              style={{
                height: "100%",
                cursor: "pointer",
                borderTop: `3px solid ${statusColor(item.color, token)}`,
                boxShadow: token.boxShadowTertiary,
              }}
            >
              <Statistic
                title={item.label}
                value={item.count}
                valueStyle={{ color: statusColor(item.color, token) }}
              />
              <Typography.Text type="secondary">点击查看该状态下的题目</Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} align="stretch">
        <Col xs={24} xl={14}>
          <div
            ref={trainingCardRef}
            style={trainingCardHeight ? { height: trainingCardHeight } : undefined}
          >
            <Card
              id="admin-training"
              className="page-section-anchor"
              style={{
                height: trainingCardHeight ? "100%" : undefined,
                boxShadow: token.boxShadowTertiary,
                display: trainingCardHeight ? "flex" : undefined,
                flexDirection: trainingCardHeight ? "column" : undefined,
              }}
              bodyStyle={
                trainingCardHeight
                  ? {
                      flex: 1,
                      display: "flex",
                      flexDirection: "column",
                      minHeight: 0,
                    }
                  : undefined
              }
              title={
                <Space>
                  <RobotOutlined style={{ color: token.colorPrimary }} />
                  <span>训练模型</span>
                </Space>
              }
              extra={<Tag color="processing">预测头训练</Tag>}
            >
              <Space size={8} wrap style={{ marginBottom: 16 }}>
                <Tag color="blue">
                  可训练样本数：{activeLearning?.completed_sample_count ?? 0}
                </Tag>
                <Tag
                  color={
                    (activeLearning?.completed_sample_count ?? 0) >= minimumTrainingSamples
                      ? "green"
                      : "red"
                  }
                >
                  最小样本数：{minimumTrainingSamples}
                </Tag>
              </Space>

              <Form
              form={trainingForm}
              layout="vertical"
              requiredMark={false}
              initialValues={{
                target_stage: "junior",
                epochs: 20,
                batch_size: 16,
                learning_rate: 0.00005,
                val_size: 0.2,
                patience: 5,
                max_length: 256,
                min_train_samples: 5,
                device: "auto",
                include_gold_labels: includeGoldLabels,
              }}
              onFinish={handleStartTraining}
            >
              <Row gutter={[16, 4]}>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="训练学段"
                    name="target_stage"
                    rules={[{ required: true }]}
                  >
                    <Select
                      options={[
                        { value: "junior", label: "初中" },
                        { value: "senior", label: "高中" },
                      ]}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Epochs" name="epochs" rules={[{ required: true }]}>
                    <InputNumber min={1} max={50} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="batch_size"
                    name="batch_size"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} max={128} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="Learning Rate"
                    name="learning_rate"
                    rules={[{ required: true }]}
                  >
                    <InputNumber
                      min={0.000001}
                      max={1}
                      step={0.00001}
                      stringMode
                      style={{ width: "100%" }}
                    />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Val Size" name="val_size" rules={[{ required: true }]}>
                    <InputNumber min={0.05} max={0.5} step={0.05} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="Patience" name="patience" rules={[{ required: true }]}>
                    <InputNumber min={1} max={50} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="Max Length"
                    name="max_length"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={32} max={512} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item
                    label="最小训练样本数"
                    name="min_train_samples"
                    rules={[{ required: true }]}
                  >
                    <InputNumber min={1} max={10000} style={{ width: "100%" }} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={8}>
                  <Form.Item label="训练设备" name="device" rules={[{ required: true }]}>
                    <Select
                      options={[
                        { value: "auto", label: "自动" },
                        { value: "cpu", label: "CPU" },
                        { value: "cuda", label: "CUDA" },
                      ]}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Space size={12} style={{ marginBottom: 16 }}>
                <Typography.Text>合并金标</Typography.Text>
                <Switch
                  checked={includeGoldLabels}
                  onChange={(checked: boolean) => {
                    setIncludeGoldLabels(checked);
                    window.localStorage.setItem(
                      TRAINING_INCLUDE_GOLD_STORAGE_KEY,
                      String(checked),
                    );
                  }}
                />
              </Space>

              <Row justify="end" gutter={12}>
                <Col>
                  <Button
                    onClick={() => void handleCancelTraining()}
                    disabled={!isTrainingActive}
                    loading={cancelTrainingMutation.isPending}
                  >
                    结束训练
                  </Button>
                </Col>
                <Col>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={trainingMutation.isPending}
                    disabled={isTrainingActive}
                  >
                    开始训练
                  </Button>
                </Col>
              </Row>
              </Form>

              <ProgressPanel
                title="训练进度"
                progress={trainingProgress.percent}
                status={trainingProgress.status}
                statusText={trainingProgress.text}
                detail={trainingProgress.detail}
              />

              <TrainingConsolePanel
                logs={latestTrainingLog?.log_text ?? ""}
                stderr={latestTrainingLog?.stderr_text ?? ""}
                isActive={isTrainingActive}
                isTruncated={latestTrainingLog?.is_truncated ?? false}
                fillAvailableHeight={Boolean(trainingCardHeight)}
              />
            </Card>
          </div>
        </Col>

        <Col xs={24} xl={10}>
          <Space
            className="admin-selection-stack"
            direction="vertical"
            size={16}
            style={{ width: "100%" }}
          >
            <div ref={predictionCardRef}>
              <Card
                id="admin-prediction"
                className="page-section-anchor"
                style={{ boxShadow: token.boxShadowTertiary }}
                title={
                  <Space>
                    <ThunderboltOutlined style={{ color: token.colorWarning }} />
                    <span>低置信度预测选题</span>
                  </Space>
                }
                extra={<Tag color="orange">模型驱动</Tag>}
              >
              <Form
                form={predictionForm}
                layout="vertical"
                requiredMark={false}
                initialValues={{
                  model_version_id: activeLearning?.active_model?.id,
                  confidence_strategy: "mean_max_probability",
                  select_count: 100,
                  batch_size: 32,
                  auto_move_to_waiting: true,
                }}
                onFinish={handleStartPrediction}
              >
                <Row gutter={[16, 4]}>
                  <Col xs={24} md={12}>
                    <Form.Item label="模型版本" name="model_version_id">
                      <Select
                        allowClear
                        placeholder="默认使用当前模型"
                        options={versionOptions}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="置信度策略"
                      name="confidence_strategy"
                      rules={[{ required: true }]}
                    >
                      <Select
                        options={[
                          { value: "mean_max_probability", label: "平均最高概率" },
                          { value: "min_max_probability", label: "最小最高概率" },
                          { value: "entropy", label: "信息熵" },
                          { value: "margin", label: "边际差值" },
                        ]}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="选题数"
                      name="select_count"
                      rules={[{ required: true }]}
                    >
                      <InputNumber min={1} max={5000} style={{ width: "100%" }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="batch_size"
                      name="batch_size"
                      rules={[{ required: true }]}
                    >
                      <InputNumber min={1} max={256} style={{ width: "100%" }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      label="进入待标注池"
                      name="auto_move_to_waiting"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Row justify="end" gutter={12}>
                  <Col>
                    <Button
                      onClick={() => void handleCancelPrediction()}
                      disabled={!isPredictionActive}
                      loading={cancelPredictionMutation.isPending}
                    >
                      结束预测
                    </Button>
                  </Col>
                  <Col>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={predictionMutation.isPending}
                      disabled={isPredictionActive || !activeLearning?.active_model}
                    >
                      预测并选题
                    </Button>
                  </Col>
                </Row>
              </Form>

              <ProgressPanel
                title="预测进度"
                progress={predictionProgress.percent}
                status={predictionProgress.status}
                statusText={predictionProgress.text}
                detail={predictionProgress.detail}
              />
              </Card>
            </div>

            <Card
              id="admin-coreset"
              className="page-section-anchor"
              style={{ boxShadow: token.boxShadowTertiary }}
              title={
                <Space>
                  <ClusterOutlined style={{ color: token.colorSuccess }} />
                  <span>CoreSet 选题</span>
                </Space>
              }
              extra={<Tag color="green">代表性采样</Tag>}
            >
              <Form
                form={coresetForm}
                layout="vertical"
                requiredMark={false}
                initialValues={{
                  strategy: "kmeans",
                  count: 400,
                  data_scope: "pending",
                  update_mode: "full",
                }}
                onFinish={(
                  values: {
                    strategy: SelectionStrategy;
                    count: number;
                    data_scope: SelectionDataScope;
                  },
                ) =>
                  void handleCoreSetSelection({
                    strategy: values.strategy as SelectionStrategy,
                    count: Number(values.count),
                    data_scope: values.data_scope as SelectionDataScope,
                    update_mode: "full",
                  })
                }
              >
                <Alert
                  showIcon
                  type={
                    hasNewUnlabeledSinceBaseline
                      ? "warning"
                      : canRunIncrementalForSelectedStrategy
                        ? "info"
                        : "warning"
                  }
                  style={{ marginBottom: 16 }}
                  message={
                    hasNewUnlabeledSinceBaseline
                      ? `上次选题后新增了 ${incrementalSummary?.new_unlabeled_count ?? 0} 道未标注题，建议使用增量更新`
                      : canRunIncrementalForSelectedStrategy
                        ? "上次选题后暂无新的未标注题"
                      : "当前算法还没有可用的增量基线"
                  }
                  description={
                    canRunIncrementalForSelectedStrategy
                      ? `当前未标注池共有 ${incrementalSummary?.current_pool_count ?? 0} 道题，增量基线 ${incrementalSummary?.baseline_batch_no ?? incrementalSummary?.baseline_run_no ?? "-"}，快照截止 ${formatDateTime(incrementalSummary?.snapshot_created_before ?? null)}。点击“开始选题”会全量重算未标注池分布；点击“增量更新未标注池”会复用该算法基线。`
                      : "请先用当前算法运行一次全量 CoreSet 选题。后续有新的未标注题加入后，系统会增量更新未标注池分布，并从当前全部未标注题中重新选题。"
                  }
                />
                <Row gutter={[16, 4]}>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="选择策略"
                      name="strategy"
                      rules={[{ required: true }]}
                    >
                      <Select options={strategyOptions} />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      label="选题数"
                      name="count"
                      rules={[{ required: true }]}
                    >
                      <InputNumber min={1} max={5000} style={{ width: "100%" }} />
                    </Form.Item>
                  </Col>
                  <Col xs={24}>
                    <Form.Item
                      label="候选题目范围"
                      name="data_scope"
                      rules={[{ required: true }]}
                    >
                      <Select
                        options={[
                          { value: "all", label: "全部题目：所有可用题目" },
                          { value: "pending", label: "未标注池：当前未标注池中的全部题目" },
                        ]}
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row justify="end">
                  <Space>
                    <Button
                      onClick={() => void handleCancelCoreset()}
                      disabled={!isCoresetActive}
                      loading={cancelCoresetMutation.isPending}
                    >
                      结束选题
                    </Button>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={coresetMutation.isPending}
                      disabled={isCoresetActive}
                    >
                      开始选题
                    </Button>
                    <Button
                      onClick={() => void handleStartIncrementalCoreSet()}
                      loading={coresetMutation.isPending}
                      disabled={
                        isCoresetActive ||
                        coresetDataScope !== "pending" ||
                        !canRunIncrementalForSelectedStrategy ||
                        !hasNewUnlabeledSinceBaseline ||
                        (incrementalSummary?.current_pool_count ?? 0) <= 0
                      }
                    >
                      增量更新未标注池
                    </Button>
                  </Space>
                </Row>
              </Form>

              <ProgressPanel
                title="CoreSet 进度"
                progress={coresetProgress.percent}
                status={coresetProgress.status}
                statusText={coresetProgress.text}
                detail={coresetProgress.detail}
              />

              {latestCoreSetResult ? (
                <Card
                  size="small"
                  title="本次 CoreSet 结果"
                  style={{ marginTop: 16, background: token.colorFillAlter }}
                >
                  <Space direction="vertical" size={12} style={{ width: "100%" }}>
                    <Alert
                      showIcon
                      type={
                        latestCoreSetResult.selected_count <= 0
                          ? "info"
                          : latestCoreSetResult.moved_count < latestCoreSetResult.selected_count
                            ? "warning"
                            : "success"
                      }
                      message={`批次 ${latestCoreSetResult.batch_no}`}
                      description={
                        latestCoreSetResult.selected_count <= 0
                          ? "本次没有选出题目，请尝试调整候选题目范围、策略或选题数量。"
                          : latestCoreSetResult.moved_count < latestCoreSetResult.selected_count
                            ? `本次共选中 ${latestCoreSetResult.selected_count} 道题，其中 ${latestCoreSetResult.moved_count} 道新进入待标注池。其余题目已不在未标注池，因此没有再次进入待标注池，但仍可查看本次算法选中的题目。`
                            : `本次共选中 ${latestCoreSetResult.selected_count} 道题，已全部进入待标注池。`
                      }
                    />
                    <Space wrap>
                      <Button
                        onClick={() =>
                          openQuestionSelection(latestCoreSetResult.question_ids)
                        }
                        disabled={latestCoreSetResult.question_ids.length <= 0}
                      >
                        查看本次选中题目
                      </Button>
                      <Button
                        onClick={() =>
                          openQuestionSelection(
                            latestCoreSetResult.moved_question_ids,
                            "WAITING",
                          )
                        }
                        disabled={latestCoreSetResult.moved_question_ids.length <= 0}
                      >
                        查看进入待标注池的题目
                      </Button>
                    </Space>
                  </Space>
                </Card>
              ) : null}
            </Card>
          </Space>
        </Col>
      </Row>

      <Card
        id="admin-pools"
        className="page-section-anchor"
        title="题池治理"
        extra={
          <Popconfirm
            title="回收题池"
            description="会把标注中的题目回收，并把待标注池中未开始的题目退回未标注池。"
            okText="确认回收"
            cancelText="取消"
            onConfirm={() => void handleResetPools()}
          >
            <Button loading={resetPoolsMutation.isPending}>
              回收标注中与待标注题目
            </Button>
          </Popconfirm>
        }
      >
        <Space direction="vertical" size={14} style={{ width: "100%" }}>
          <Typography.Text type="secondary">
            这里集中查看 CoreSet / 低置信度选题批次，并支持按批次撤回，以及回收标注中和待标注的题目。
          </Typography.Text>
          <Table<SelectionBatchSummary>
            rowKey="id"
            size="small"
            pagination={{ pageSize: 8, showSizeChanger: false }}
            dataSource={selectionBatches}
            columns={selectionBatchColumns}
            locale={{ emptyText: "暂无可治理的选题批次" }}
          />
        </Space>
      </Card>

      <Card
        id="admin-coreset-history"
        className="page-section-anchor"
        title="CoreSet 历史任务"
      >
        <Table<CoresetRun>
          rowKey="id"
          size="small"
          pagination={{ pageSize: 8, showSizeChanger: false }}
          dataSource={activeLearning?.coreset_runs ?? []}
          columns={coresetRunColumns}
          locale={{ emptyText: "暂无 CoreSet 历史任务" }}
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
                <Tag color={getRunStatusColor(selectedCoresetRun.status)}>
                  {getRunStatusLabel(selectedCoresetRun.status)}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="运行阶段">
                {String(
                  selectedCoresetRun.metrics_json?.progress_label ??
                    selectedCoresetRun.metrics_json?.phase ??
                    "-",
                )}
              </Descriptions.Item>
              <Descriptions.Item label="策略">
                {formatAlgorithmLabel(selectedCoresetRun.strategy)}
              </Descriptions.Item>
              <Descriptions.Item label="候选题目范围">
                {selectedCoresetRun.data_scope === "pending" ? "未标注池中的题目" : "全部题目"}
              </Descriptions.Item>
              <Descriptions.Item label="更新模式">
                {selectedCoresetRun.update_mode === "incremental" ? "增量更新" : "全量选题"}
              </Descriptions.Item>
              <Descriptions.Item label="基线批次">
                {selectedCoresetRun.baseline_batch_no ??
                  selectedCoresetRun.baseline_run_no ??
                  "-"}
              </Descriptions.Item>
              <Descriptions.Item label="请求数">
                {selectedCoresetRun.requested_count}
              </Descriptions.Item>
              <Descriptions.Item label="候选数">
                {selectedCoresetRun.candidate_count}
              </Descriptions.Item>
              <Descriptions.Item label="当前未标注池">
                {String(selectedCoresetRun.metrics_json?.current_pool_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="较基线新增">
                {String(selectedCoresetRun.metrics_json?.new_unlabeled_count ?? "-")}
              </Descriptions.Item>
              <Descriptions.Item label="选中数">
                {selectedCoresetRun.selected_count}
              </Descriptions.Item>
              <Descriptions.Item label="进入待标注池数量">
                {selectedCoresetRun.moved_count}
              </Descriptions.Item>
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
                {formatDateTime(
                  (selectedCoresetRun.metrics_json?.snapshot_created_before as
                    | string
                    | null
                    | undefined) ?? null,
                )}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatDateTime(selectedCoresetRun.created_at)}
              </Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {selectedCoresetRun.finished_at
                  ? formatDateTime(selectedCoresetRun.finished_at)
                  : "-"}
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
              <Alert
                type="error"
                showIcon
                message="失败原因"
                description={selectedCoresetRun.error_message}
              />
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
              <Button
                onClick={() => openQuestionSelection(selectedCoresetRun.question_ids)}
                disabled={selectedCoresetRun.question_ids.length <= 0}
              >
                查看本次选中题目
              </Button>
              <Button
                onClick={() =>
                  openQuestionSelection(
                    selectedCoresetRun.moved_question_ids,
                    "WAITING",
                  )
                }
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

function latestRun<T>(items?: T[]) {
  return items?.[0] ?? null;
}

function getTrainingProgress(run: TrainingRun | null): ProgressInfo {
  if (!run) {
    return {
      percent: 0,
      status: "normal",
      text: "暂无训练任务",
      detail: "点击开始训练后，这里会显示最新训练任务的执行状态。",
    };
  }

  const totalEpochs = Math.max(
    1,
    numberFromParams(run.params_json, "epochs", run.epochs.length),
  );
  const completedEpochs = run.epochs.length;

  if (run.status === "SUCCESS") {
    return {
      percent: 100,
      status: "success",
      text: `${run.run_no} 已完成`,
      detail: `完成 ${completedEpochs}/${totalEpochs} 个 epoch，训练/验证样本 ${run.train_sample_count}/${run.val_sample_count}。`,
    };
  }

  if (run.status === "FAILED") {
    return {
      percent: Math.min(
        99,
        Math.round((completedEpochs / Math.max(totalEpochs, 1)) * 100),
      ),
      status: "exception",
      text: `${run.run_no} 失败`,
      detail: run.error_message ?? "训练任务执行失败。",
    };
  }

  return {
    percent:
      run.status === "PENDING"
        ? 3
        : Math.max(
            5,
            Math.min(
              95,
              Math.round((completedEpochs / Math.max(totalEpochs, 1)) * 100),
            ),
          ),
    status: run.status === "RUNNING" ? "active" : "normal",
    text: `${run.run_no} ${run.status === "RUNNING" ? "训练中" : "等待执行"}`,
    detail: `已记录 ${completedEpochs}/${totalEpochs} 个 epoch，训练/验证样本 ${run.train_sample_count}/${run.val_sample_count}。`,
  };
}

function getPredictionProgress(run: PredictionRun | null): ProgressInfo {
  if (!run) {
    return {
      percent: 0,
      status: "normal",
      text: "暂无预测任务",
      detail: "点击预测并选题后，这里会显示最新预测任务的执行状态。",
    };
  }

  const selectCount = numberFromParams(
    run.params_json,
    "select_count",
    run.selected_count,
  );
  const processedCount = numberFromParams(run.metrics_json, "processed_count", 0);
  const totalCount = numberFromParams(
    run.metrics_json,
    "total_count",
    run.candidate_count,
  );
  const batchSize = numberFromParams(run.metrics_json, "batch_size", 0);

  if (run.status === "SUCCESS") {
    return {
      percent: 100,
      status: "success",
      text: `${run.run_no} 已完成`,
      detail: `候选 ${run.candidate_count} 题，选中 ${run.selected_count}/${selectCount} 题，进入待标注池 ${run.moved_count} 题。`,
    };
  }

  if (run.status === "FAILED") {
    return {
      percent: 0,
      status: "exception",
      text: `${run.run_no} 失败`,
      detail: run.error_message ?? "预测任务执行失败。",
    };
  }

  return {
    percent:
      run.status === "RUNNING"
        ? totalCount > 0
          ? Math.max(5, Math.min(95, Math.round((processedCount / totalCount) * 100)))
          : 8
        : 5,
    status: run.status === "RUNNING" ? "active" : "normal",
    text: `${run.run_no} ${run.status === "RUNNING" ? "预测中" : "等待执行"}`,
    detail:
      run.status === "RUNNING"
        ? `目标选题 ${selectCount} 题，当前已处理 ${processedCount}/${totalCount}，batch_size=${batchSize || "-"}。`
        : `目标选题 ${selectCount} 题，候选题目范围为全部未标注题。`,
  };
}

function getCoreSetProgress(run: CoresetRun | null): ProgressInfo {
  if (!run) {
    return {
      percent: 0,
      status: "normal",
      text: "暂无 CoreSet 任务",
      detail: "点击开始选题后，这里会显示最新 CoreSet 后台任务的执行状态。",
    };
  }

  const progressPercent = numberFromParams(run.metrics_json, "progress_percent", 0);
  const progressLabel = String(run.metrics_json?.progress_label ?? "");
  const processedCount = numberFromParams(run.metrics_json, "processed_count", 0);
  const totalCount = numberFromParams(
    run.metrics_json,
    "total_count",
    run.candidate_count,
  );
  const selectionMode = String(run.metrics_json?.selection_mode ?? "");

  if (run.status === "SUCCESS") {
    return {
      percent: 100,
      status: "success",
      text: `${run.batch_no ?? run.run_no} 已完成`,
      detail: `候选 ${run.candidate_count} 题，选中 ${run.selected_count}/${run.requested_count} 题，进入待标注池 ${run.moved_count} 题。`,
    };
  }

  if (run.status === "FAILED") {
    return {
      percent: 0,
      status: "exception",
      text: `${run.run_no} 失败`,
      detail: run.error_message ?? "CoreSet 后台任务执行失败。",
    };
  }

  return {
    percent:
      run.status === "RUNNING"
        ? Math.max(5, Math.min(95, progressPercent || 10))
        : 5,
    status: run.status === "RUNNING" ? "active" : "normal",
    text: `${run.run_no} ${progressLabel || (run.status === "RUNNING" ? "运行中" : "等待执行")}`,
    detail:
      totalCount > 0
        ? `候选池 ${run.candidate_count} 题，当前已处理 ${processedCount}/${totalCount}，模式：${selectionMode || "-"}。`
        : `候选池准备中，目标选题 ${run.requested_count} 题，模式：${selectionMode || "-"}。`,
  };
}

function numberFromParams(
  params: Record<string, unknown> | null | undefined,
  key: string,
  fallback: number,
) {
  const value = params?.[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function statusColor(
  color: string,
  token: {
    colorPrimary: string;
    colorSuccess: string;
    colorWarning: string;
  },
) {
  const colors: Record<string, string> = {
    blue: token.colorPrimary,
    green: token.colorSuccess,
    orange: token.colorWarning,
    gold: "#d48806",
    purple: "#722ed1",
  };
  return colors[color] ?? token.colorPrimary;
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
  return coreSetAlgorithms.has(value as SelectionStrategy)
    ? "CoreSet 选题"
    : "低置信度选题";
}

function annotationPolicySyncAlertType(
  status: AnnotationPolicySyncStatus["status"],
): "info" | "success" | "warning" | "error" {
  if (status === "running") return "info";
  if (status === "completed") return "success";
  if (status === "failed") return "error";
  return "warning";
}

function annotationPolicySyncMessage(syncStatus: AnnotationPolicySyncStatus) {
  if (syncStatus.status === "running") {
    return `后台正在同步 ${syncStatus.target_annotator_count} 人策略`;
  }
  if (syncStatus.status === "completed") {
    return `后台同步已完成，共更新 ${syncStatus.updated_question_count} 道未开工题`;
  }
  if (syncStatus.status === "failed") {
    return "后台同步失败";
  }
  return "当前没有待处理的后台同步任务";
}

function annotationPolicySyncDescription(syncStatus: AnnotationPolicySyncStatus) {
  if (syncStatus.status === "running") {
    return `${syncStatus.affected_question_count} 道未开工题正在按 ${syncStatus.target_annotator_count} 人策略回填，发起时间 ${formatDateTime(syncStatus.started_at)}。`;
  }
  if (syncStatus.status === "completed") {
    return `${syncStatus.updated_question_count} / ${syncStatus.affected_question_count} 道未开工题已同步完成，完成时间 ${formatDateTime(syncStatus.finished_at)}。`;
  }
  if (syncStatus.status === "failed") {
    return syncStatus.error_message
      ? `失败原因：${syncStatus.error_message}`
      : "后台任务执行失败，请稍后重试。";
  }
  if (syncStatus.finished_at) {
    return `上次完成时间 ${formatDateTime(syncStatus.finished_at)}。`;
  }
  return "切换标注人数后，系统会在后台同步尚未开工的题目。";
}


function ProgressPanel({
  title,
  progress,
  status,
  statusText,
  detail,
}: {
  title: string;
  progress: number;
  status: ProgressStatus;
  statusText: string;
  detail: string;
}) {
  return (
    <div style={{ marginTop: 18 }}>
      <Space
        direction="vertical"
        size={10}
        style={{ width: "100%", padding: "2px 0" }}
      >
        <Row justify="space-between" align="middle">
          <Typography.Text strong>{title}</Typography.Text>
          <Tag
            color={
              status === "success"
                ? "green"
                : status === "exception"
                  ? "red"
                  : status === "active"
                    ? "processing"
                    : "default"
            }
          >
            {statusText}
          </Tag>
        </Row>
        <Progress percent={progress} status={status} />
        <Typography.Text type="secondary">{detail}</Typography.Text>
      </Space>
    </div>
  );
}

function TrainingConsolePanel({
  logs,
  stderr,
  isActive,
  isTruncated,
  fillAvailableHeight,
}: {
  logs: string;
  stderr: string;
  isActive: boolean;
  isTruncated: boolean;
  fillAvailableHeight?: boolean;
}) {
  const output = [logs, stderr].filter(Boolean).join("\n\n");

  return (
    <div
      style={{
        marginTop: 18,
        flex: fillAvailableHeight ? 1 : undefined,
        minHeight: fillAvailableHeight ? 0 : undefined,
        display: fillAvailableHeight ? "flex" : undefined,
        flexDirection: fillAvailableHeight ? "column" : undefined,
      }}
    >
      <Row justify="space-between" align="middle" style={{ marginBottom: 8 }}>
        <Space size={8}>
          <Typography.Text strong>训练控制台</Typography.Text>
          {isActive ? <Tag color="processing">实时刷新</Tag> : <Tag>最近一次输出</Tag>}
          {isTruncated ? <Tag color="gold">仅显示末尾日志</Tag> : null}
        </Space>
      </Row>
      <pre
        style={{
          flex: fillAvailableHeight ? 1 : undefined,
          margin: 0,
          padding: 16,
          height: fillAvailableHeight ? undefined : 320,
          minHeight: fillAvailableHeight ? 160 : undefined,
          overflow: "auto",
          borderRadius: 12,
          background: "#0f172a",
          color: "#e2e8f0",
          fontSize: 12,
          lineHeight: 1.6,
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {output ||
          "暂无训练日志。新启动的训练任务会在这里显示模型加载、batch loss 和 epoch 指标。"}
      </pre>
    </div>
  );
}
