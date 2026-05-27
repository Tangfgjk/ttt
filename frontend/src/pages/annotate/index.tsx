import { ClockCircleOutlined, InboxOutlined, SendOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  InputNumber,
  List,
  Popconfirm,
  Progress,
  Radio,
  Row,
  Segmented,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";

import { useAuthStore } from "@/app/store/auth-store";
import { CompetencyHelpPopover } from "@/components/competency-help-popover";
import { QuestionRichText } from "@/components/question-rich-text";
import {
  getAnnotationStatusColor,
  getAnnotationStatusLabel,
  getAnnotationTaskStatusLabel,
} from "@/constants/annotation-status";
import {
  useAnnotationPoolSummary,
  useAnnotationTasks,
  useClaimAnnotationTasks,
  useReviseAnnotationTask,
  useSubmitAnnotationTask,
} from "@/modules/annotations/hooks";
import { useCompetencies, useQuestionDetail } from "@/modules/question-bank/hooks";
import { useTrainingModule } from "@/modules/training/hooks";
import type { CompetencyItem } from "@/types/dictionary";
import type { AnnotationTask } from "@/types/annotations";
import type { QuestionDetail } from "@/types/question";
import type { TrainingStage } from "@/types/training";

type AnnotationFormValues = {
  confidence_level?: number;
  competencies?: Record<number, number>;
  competency_confidence_levels?: Record<number, number>;
};

type SubmittedAnnotationDraft = {
  task: AnnotationTask;
  values: {
    confidence_level: number;
    competencies: Record<number, number>;
    competency_confidence_levels: Record<number, number>;
  };
  canRevise: boolean;
};

const CONFIDENCE_OPTIONS = [
  { label: "高", value: 5 },
  { label: "中", value: 3 },
  { label: "低", value: 1 },
];

const DETAIL_VIEW_MODE_OPTIONS = [
  { label: "渲染视图", value: "rendered" },
  { label: "原始文本", value: "raw" },
] as const;

type DetailViewMode = (typeof DETAIL_VIEW_MODE_OPTIONS)[number]["value"];

const JUNIOR_COMPETENCY_CODES = new Set([
  "abstraction",
  "operation",
  "geometric_intuition",
  "spatial_conception",
  "reasoning",
  "data_consciousness",
  "model_consciousness",
  "application_awareness",
  "innovation_awareness",
]);

const SENIOR_COMPETENCY_CODES = new Set([
  "mathematical_abstraction",
  "logical_reasoning",
  "mathematical_modeling",
  "intuitive_imagination",
  "mathematical_operation",
  "data_analysis",
]);

function resolveEduStage(task: AnnotationTask | null) {
  const grade = task?.question.grade;
  if (grade?.edu_stage) {
    return grade.edu_stage;
  }

  const gradeIndex = grade?.grade_index;
  if (gradeIndex && gradeIndex >= 7 && gradeIndex <= 9) {
    return "junior";
  }
  if (gradeIndex && gradeIndex >= 10 && gradeIndex <= 12) {
    return "senior";
  }

  return null;
}

function filterCompetenciesByStage(
  items: CompetencyItem[] | undefined,
  eduStage: string | null,
) {
  if (!items?.length) {
    return [];
  }
  if (eduStage === "junior") {
    return items.filter((item) => JUNIOR_COMPETENCY_CODES.has(item.code));
  }
  if (eduStage === "senior") {
    return items.filter((item) => SENIOR_COMPETENCY_CODES.has(item.code));
  }
  return items;
}

function RawTextBlock({ value, emptyLabel = "暂无内容" }: { value?: string | null; emptyLabel?: string }) {
  if (!value) {
    return <Typography.Text type="secondary">{emptyLabel}</Typography.Text>;
  }
  return <pre className="question-raw-block">{value}</pre>;
}

function renderDifficultyStats(detail: QuestionDetail) {
  if (!detail.difficulty_level_stats.length) {
    return <Typography.Text type="secondary">暂无难度等级统计</Typography.Text>;
  }

  return (
    <Space size={[8, 8]} wrap>
      {detail.difficulty_level_stats.map((item) => (
        <Tag key={item.level} color={detail.source_difficulty_level === item.level ? "processing" : "default"}>
          {`L${item.level} · ${item.question_count}题`}
        </Tag>
      ))}
    </Space>
  );
}

function AnnotationQuestionDetail({
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
          options={DETAIL_VIEW_MODE_OPTIONS.map((item) => ({ label: item.label, value: item.value }))}
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
            children: (
              <Tag color={getAnnotationStatusColor(detail.annotation_status)}>
                {getAnnotationStatusLabel(detail.annotation_status)}
              </Tag>
            ),
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

      <Card size="small" title="答案">
        {isRawMode ? (
          <RawTextBlock value={detail.content?.answer_text} />
        ) : (
          <QuestionRichText text={detail.content?.answer_text} />
        )}
      </Card>

      <Card size="small" title="解析">
        {isRawMode ? (
          <RawTextBlock value={detail.content?.solution_text} />
        ) : (
          <QuestionRichText text={detail.content?.solution_text} />
        )}
      </Card>
    </Space>
  );
}

export function AnnotatePage() {
  const [form] = Form.useForm();
  const session = useAuthStore((state) => state.session);
  const userId = session?.id ?? null;
  const [claimCount, setClaimCount] = useState(50);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [detailViewMode, setDetailViewMode] = useState<DetailViewMode>("rendered");
  const { data: taskData, isLoading } = useAnnotationTasks(userId, "IN_PROGRESS");
  const { data: poolSummary } = useAnnotationPoolSummary();
  const { data: competencies } = useCompetencies();
  const claimMutation = useClaimAnnotationTasks();
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [lastSubmittedTask, setLastSubmittedTask] = useState<SubmittedAnnotationDraft | null>(null);
  const [isRevisingLastSubmitted, setIsRevisingLastSubmitted] = useState(false);
  const activeTask = useMemo(
    () => taskData?.items.find((item) => item.id === activeTaskId) ?? taskData?.items[0] ?? null,
    [activeTaskId, taskData?.items],
  );
  const displayTask = isRevisingLastSubmitted ? lastSubmittedTask?.task ?? null : activeTask;
  const submitMutation = useSubmitAnnotationTask(activeTask?.id ?? null);
  const reviseMutation = useReviseAnnotationTask(lastSubmittedTask?.task.id ?? null);
  const activeMutation = isRevisingLastSubmitted ? reviseMutation : submitMutation;
  const activeEduStage = useMemo(() => resolveEduStage(displayTask), [displayTask]);
  const visibleCompetencies = useMemo(
    () => filterCompetenciesByStage(competencies, activeEduStage),
    [activeEduStage, competencies],
  );
  const trainingModuleQuery = useTrainingModule(
    userId,
    (activeEduStage as TrainingStage | null) ?? null,
  );
  const competencyDefinitionMap = useMemo(
    () =>
      new Map(
        (trainingModuleQuery.data?.competency_definitions ?? []).map((item) => [item.code, item]),
      ),
    [trainingModuleQuery.data?.competency_definitions],
  );
  const questionDetailQuery = useQuestionDetail(displayTask?.question_id ?? null);

  useEffect(() => {
    if (!isRevisingLastSubmitted && activeTask && activeTask.id !== activeTaskId) {
      setActiveTaskId(activeTask.id);
    }
  }, [activeTask, activeTaskId, isRevisingLastSubmitted]);

  useEffect(() => {
    if (!displayTask || !visibleCompetencies.length) {
      return;
    }
    if (isRevisingLastSubmitted && lastSubmittedTask?.task.id === displayTask.id) {
      form.setFieldsValue({
        confidence_level: lastSubmittedTask.values.confidence_level,
        competencies: Object.fromEntries(
          visibleCompetencies.map((item) => [
            item.id,
            lastSubmittedTask.values.competencies[item.id] ?? 0,
          ]),
        ),
        competency_confidence_levels: Object.fromEntries(
          visibleCompetencies.map((item) => [
            item.id,
            lastSubmittedTask.values.competency_confidence_levels[item.id] ?? 5,
          ]),
        ),
      });
      return;
    }
    form.setFieldsValue({
      confidence_level: 5,
      competencies: Object.fromEntries(visibleCompetencies.map((item) => [item.id, 0])),
      competency_confidence_levels: Object.fromEntries(
        visibleCompetencies.map((item) => [item.id, 5]),
      ),
    });
  }, [
    displayTask?.id,
    form,
    isRevisingLastSubmitted,
    lastSubmittedTask,
    visibleCompetencies,
  ]);

  const waitingCount =
    poolSummary?.items.find((item) => item.status === "WAITING")?.count ?? 0;
  const inProgressCount =
    poolSummary?.items.find((item) => item.status === "IN_PROGRESS")?.count ?? 0;
  const claimableCount = waitingCount + inProgressCount;

  useEffect(() => {
    if (claimableCount <= 0) {
      return;
    }
    if (claimCount > claimableCount) {
      setClaimCount(claimableCount);
    }
  }, [claimCount, claimableCount]);

  const handleClaim = async () => {
    if (!userId) {
      message.error("请先登录");
      return;
    }
    if (claimableCount <= 0) {
      message.info("当前没有可领取题目。");
      return;
    }
    const result = await claimMutation.mutateAsync({
      annotator_user_id: userId,
      count: Math.min(claimCount, claimableCount),
    });
    message.success(`已领取 ${result.claimed_count} 道题`);
  };

  const handleSubmit = async (values: AnnotationFormValues) => {
    if (!userId || !displayTask) {
      return;
    }
    const competencyValues = values.competencies ?? {};
    const confidenceValues = values.competency_confidence_levels ?? {};
    const competencyPayload = visibleCompetencies.map((item) => ({
      competency_id: item.id,
      level_value: competencyValues[item.id] ?? 0,
      confidence_level: confidenceValues[item.id] ?? 5,
    }));
    const normalizedValues = {
      confidence_level: values.confidence_level ?? 5,
      competencies: Object.fromEntries(
        visibleCompetencies.map((item) => [item.id, competencyValues[item.id] ?? 0]),
      ),
      competency_confidence_levels: Object.fromEntries(
        visibleCompetencies.map((item) => [item.id, confidenceValues[item.id] ?? 5]),
      ),
    };
    const result = await activeMutation.mutateAsync({
      annotator_user_id: userId,
      cognitive_level_id: null,
      competencies: competencyPayload,
    });
    setLastSubmittedTask({
      task: displayTask,
      values: normalizedValues,
      canRevise: result.question_status === "WAITING" || result.question_status === "IN_PROGRESS",
    });
    message.success(
      isRevisingLastSubmitted
        ? `已更新上一题标注，当前 ${result.annotation_count}/${result.required_annotations}`
        : result.is_disputed
          ? "已提交，当前题目存在分歧，已进入待复核池"
          : `已提交，当前 ${result.annotation_count}/${result.required_annotations}`,
    );
    form.resetFields();
    if (isRevisingLastSubmitted) {
      setIsRevisingLastSubmitted(false);
      setActiveTaskId(activeTask?.id ?? null);
    } else {
      setActiveTaskId(null);
    }
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={8}>
        <Card
          title="我的待标注任务"
          extra={
            <Space>
              <InputNumber
                min={1}
                max={Math.max(claimableCount, 1)}
                value={claimCount}
                onChange={(value: number | null) => setClaimCount(Number(value) || 1)}
              />
              <Button
                icon={<InboxOutlined />}
                onClick={handleClaim}
                loading={claimMutation.isPending}
                disabled={claimableCount <= 0}
              >
                领取题目
              </Button>
            </Space>
          }
        >
          <Typography.Text type="secondary">
            当前可领取题目还有 {claimableCount} 道，其中待标注池 {waitingCount} 道、标注中 {inProgressCount} 道。
          </Typography.Text>
          {!isLoading && !taskData?.items.length ? (
            <Empty description="暂无已领取任务，可从待标注池领取" />
          ) : (
            <List
              loading={isLoading}
              dataSource={taskData?.items ?? []}
              renderItem={(item: AnnotationTask) => (
                <List.Item
                  onClick={() => {
                    setIsRevisingLastSubmitted(false);
                    setActiveTaskId(item.id);
                  }}
                  style={{
                    cursor: "pointer",
                    background: item.id === activeTask?.id ? "#e6f4ff" : undefined,
                    paddingInline: 8,
                    borderRadius: 6,
                  }}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <span>任务 #{item.id}</span>
                        <Tag color="cyan">题目 #{item.question_id}</Tag>
                        <Tag icon={<ClockCircleOutlined />}>
                          {getAnnotationTaskStatusLabel(item.task_status)}
                        </Tag>
                      </Space>
                    }
                    description={item.question.content?.stem_text?.slice(0, 64) ?? "暂无题干"}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </Col>

      <Col xs={24} xl={16}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Card title="标注工作台">
            {displayTask ? (
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                <Space wrap>
                  <Tag color="blue">题目 #{displayTask.question_id}</Tag>
                  <Tag>{displayTask.question.subject.name}</Tag>
                  {displayTask.question.grade ? <Tag>{displayTask.question.grade.grade_name}</Tag> : null}
                  {displayTask.question.question_type ? (
                    <Tag>{displayTask.question.question_type.name}</Tag>
                  ) : null}
                  {isRevisingLastSubmitted ? <Tag color="orange">正在修改上一题</Tag> : null}
                  <Tag color="processing">
                    已提交 {displayTask.progress.submitted_annotation_count}/
                    {displayTask.progress.required_annotations}
                  </Tag>
                  <Tag color="purple">
                    并行中 {displayTask.progress.active_annotation_count}
                  </Tag>
                  <Button size="small" onClick={() => setDetailDrawerOpen(true)}>
                    查看详情
                  </Button>
                </Space>
                <Progress
                  percent={displayTask.progress.progress_percent}
                  size="small"
                  status="active"
                />
                <Typography.Text type="secondary">
                  当前题目支持多人并行标注，系统会实时同步标注进度；当达到当前要求人数后，
                  系统会自动聚合结果，若仍存在分歧则进入复核流程。
                </Typography.Text>
                <QuestionRichText
                  html={displayTask.question.content?.stem_html}
                  text={displayTask.question.content?.stem_text}
                  emptyLabel="暂无题干"
                />
              </Space>
            ) : (
              <Empty description="请选择或领取一道题开始标注" />
            )}
          </Card>

          <Card title="提交标注">
            {!displayTask ? (
              <Alert type="info" showIcon message="领取任务后即可填写认知层级和核心素养矩阵。" />
            ) : (
              <Form form={form} layout="vertical" onFinish={handleSubmit}>
                {lastSubmittedTask?.canRevise ? (
                  <Alert
                    type={isRevisingLastSubmitted ? "warning" : "info"}
                    showIcon
                    message={
                      isRevisingLastSubmitted
                        ? "正在修改上一题，重新提交后会覆盖你刚才的标注。"
                        : "刚提交的上一题可返回修改，直到该题进入聚合或复核。"
                    }
                    action={
                      isRevisingLastSubmitted ? (
                        <Button
                          size="small"
                          onClick={() => {
                            setIsRevisingLastSubmitted(false);
                            setActiveTaskId(null);
                          }}
                        >
                          取消修改
                        </Button>
                      ) : (
                        <Popconfirm
                          title="返回上一题修改？"
                          description="当前会切回你刚提交的上一题，并带出刚才的标注结果。"
                          okText="返回修改"
                          cancelText="继续当前题"
                          onConfirm={() => {
                            setIsRevisingLastSubmitted(true);
                            setDetailDrawerOpen(false);
                          }}
                        >
                          <Button size="small">返回上一题修改</Button>
                        </Popconfirm>
                      )
                    }
                    style={{ marginBottom: 16 }}
                  />
                ) : null}

                <Alert
                  type="info"
                  showIcon
                  message="信心等级现在按每个素养分别填写，默认高；它表示你对该素养层级判断的把握程度，会随标注结果提供给复核员参考。"
                  style={{ marginBottom: 16 }}
                />

                <Space direction="vertical" size={14} style={{ width: "100%" }}>
                  {visibleCompetencies.map((item) => {
                    const definition = competencyDefinitionMap.get(item.code);
                    return (
                    <div key={item.id} className="matrix-row">
                      <CompetencyHelpPopover
                        name={item.name}
                        definition={definition?.definition}
                        focusTip={definition?.focus_tip}
                      />
                      <Form.Item name={["competencies", item.id]} noStyle>
                        <Radio.Group
                          options={[
                            { label: "0", value: 0 },
                            { label: "1", value: 1 },
                            { label: "2", value: 2 },
                            { label: "3", value: 3 },
                          ]}
                          optionType="button"
                          buttonStyle="solid"
                        />
                      </Form.Item>
                      <Space size={6} wrap>
                        <Typography.Text type="secondary">信心等级</Typography.Text>
                        <Form.Item name={["competency_confidence_levels", item.id]} noStyle>
                          <Radio.Group
                            options={CONFIDENCE_OPTIONS}
                            optionType="button"
                            buttonStyle="solid"
                          />
                        </Form.Item>
                      </Space>
                    </div>
                    );
                  })}
                </Space>

                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SendOutlined />}
                  loading={activeMutation.isPending}
                  style={{ marginTop: 16 }}
                >
                  {isRevisingLastSubmitted ? "重新提交修改" : "提交标注"}
                </Button>
              </Form>
            )}
          </Card>
        </Space>
      </Col>

      <Drawer
        title={displayTask ? `题目 #${displayTask.question_id}` : "题目详情"}
        width={880}
        open={detailDrawerOpen}
        onClose={() => setDetailDrawerOpen(false)}
        destroyOnClose
      >
        {!displayTask ? (
          <Empty description="当前没有可查看的题目" />
        ) : questionDetailQuery.data ? (
          <AnnotationQuestionDetail
            detail={questionDetailQuery.data}
            viewMode={detailViewMode}
            onViewModeChange={setDetailViewMode}
          />
        ) : (
          <Empty description="未找到题目详情" />
        )}
      </Drawer>
    </Row>
  );
}
