import { ClockCircleOutlined, InboxOutlined, SendOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  InputNumber,
  List,
  Progress,
  Radio,
  Row,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";

import { useAuthStore } from "@/app/store/auth-store";
import { CompetencyHelpPopover } from "@/components/competency-help-popover";
import { QuestionDetailSections } from "@/components/question-detail-sections";
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
  useSubmitAnnotationTask,
} from "@/modules/annotations/hooks";
import { useCompetencies, useQuestionDetail } from "@/modules/question-bank/hooks";
import { useTrainingModule } from "@/modules/training/hooks";
import type { CompetencyItem } from "@/types/dictionary";
import type { AnnotationTask } from "@/types/annotations";
import type { TrainingStage } from "@/types/training";

type AnnotationFormValues = {
  confidence_level?: number;
  competencies?: Record<number, number>;
  competency_confidence_levels?: Record<number, number>;
};

const CONFIDENCE_OPTIONS = [
  { label: "高", value: 5 },
  { label: "中", value: 3 },
  { label: "低", value: 1 },
];

const MAX_SELECTED_COMPETENCIES = 3;

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

function countSelectedCompetencies(values?: Record<number, number>) {
  return Object.values(values ?? {}).filter((value) => Number(value) > 0).length;
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

export function AnnotatePage() {
  const [form] = Form.useForm();
  const session = useAuthStore((state) => state.session);
  const userId = session?.id ?? null;
  const [claimCount, setClaimCount] = useState(50);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const { data: taskData, isLoading } = useAnnotationTasks(userId, "IN_PROGRESS");
  const { data: poolSummary } = useAnnotationPoolSummary();
  const { data: competencies } = useCompetencies();
  const claimMutation = useClaimAnnotationTasks();
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const activeTask = useMemo(
    () => taskData?.items.find((item) => item.id === activeTaskId) ?? taskData?.items[0] ?? null,
    [activeTaskId, taskData?.items],
  );
  const displayTask = activeTask;
  const submitMutation = useSubmitAnnotationTask(activeTask?.id ?? null);
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
    if (activeTask && activeTask.id !== activeTaskId) {
      setActiveTaskId(activeTask.id);
    }
  }, [activeTask, activeTaskId]);

  useEffect(() => {
    if (!displayTask || !visibleCompetencies.length) {
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
    if (countSelectedCompetencies(competencyValues) > MAX_SELECTED_COMPETENCIES) {
      message.warning(`最多只能标注 ${MAX_SELECTED_COMPETENCIES} 个最核心的素养`);
      return;
    }
    const confidenceValues = values.competency_confidence_levels ?? {};
    const competencyPayload = visibleCompetencies.map((item) => ({
      competency_id: item.id,
      level_value: competencyValues[item.id] ?? 0,
      confidence_level: confidenceValues[item.id] ?? 5,
    }));
    let result;
    try {
      result = await submitMutation.mutateAsync({
        annotator_user_id: userId,
        cognitive_level_id: null,
        competencies: competencyPayload,
      });
    } catch (error) {
      const detail = (error as { response?: { data?: { detail?: string } }; message?: string })
        .response?.data?.detail;
      message.error(detail || (error as Error).message || "提交失败，请稍后重试");
      return;
    }
    message.success(
      result.is_disputed
        ? "已提交，当前题目存在分歧，已进入待复核池"
        : `已提交，当前 ${result.annotation_count}/${result.required_annotations}`,
    );
    form.resetFields();
    setActiveTaskId(null);
  };

  const handleValuesChange = (
    changedValues: Partial<AnnotationFormValues>,
    allValues: AnnotationFormValues,
  ) => {
    if (countSelectedCompetencies(allValues.competencies) <= MAX_SELECTED_COMPETENCIES) {
      return;
    }
    const changedCompetencyId = Number(Object.keys(changedValues.competencies ?? {})[0]);
    if (changedCompetencyId) {
      form.setFieldsValue({
        competencies: {
          ...(allValues.competencies ?? {}),
          [changedCompetencyId]: 0,
        },
      });
    }
    message.warning(`每题最多标注 ${MAX_SELECTED_COMPETENCIES} 个最核心的素养`);
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
              <Form
                form={form}
                layout="vertical"
                onFinish={handleSubmit}
                onValuesChange={handleValuesChange}
              >
                <Alert
                  type="info"
                  showIcon
                  message="信心等级现在按每个素养分别填写，默认高；它表示你对该素养层级判断的把握程度，会随标注结果提供给复核员参考。"
                  style={{ marginBottom: 16 }}
                />
                <Alert
                  type="info"
                  showIcon
                  message={`请只标注 ${MAX_SELECTED_COMPETENCIES} 个以内最核心的素养，其他相关性较弱的素养保持 0。`}
                  style={{ marginBottom: 16 }}
                />
                <Alert
                  type="info"
                  showIcon
                  message="可以点击题目右上角的“查看详情”，阅览题目难度、知识点、目录、来源映射等详细信息。"
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
                      <Space size={6} wrap>
                        <Typography.Text type="secondary">素养水平</Typography.Text>
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
                      </Space>
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

                <Space wrap style={{ marginTop: 16 }}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SendOutlined />}
                    loading={submitMutation.isPending}
                  >
                    提交标注
                  </Button>
                </Space>
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
          <QuestionDetailSections detail={questionDetailQuery.data} />
        ) : (
          <Empty description="未找到题目详情" />
        )}
      </Drawer>
    </Row>
  );
}
