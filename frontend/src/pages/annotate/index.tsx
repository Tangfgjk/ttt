import { ClockCircleOutlined, InboxOutlined, SendOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
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
import { QuestionRichText } from "@/components/question-rich-text";
import {
  useAnnotationPoolSummary,
  useAnnotationTasks,
  useClaimAnnotationTasks,
  useSubmitAnnotationTask,
} from "@/modules/annotations/hooks";
import { useCompetencies } from "@/modules/question-bank/hooks";
import { useTrainingModule } from "@/modules/training/hooks";
import type { CompetencyItem } from "@/types/dictionary";
import type { AnnotationTask } from "@/types/annotations";
import type { TrainingStage } from "@/types/training";

type AnnotationFormValues = {
  confidence_level?: number;
  competencies?: Record<number, number>;
};

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

export function AnnotatePage() {
  const [form] = Form.useForm();
  const session = useAuthStore((state) => state.session);
  const userId = session?.id ?? null;
  const [claimCount, setClaimCount] = useState(10);
  const { data: taskData, isLoading } = useAnnotationTasks(userId, "IN_PROGRESS");
  const { data: poolSummary } = useAnnotationPoolSummary();
  const { data: competencies } = useCompetencies();
  const claimMutation = useClaimAnnotationTasks();
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const activeTask = useMemo(
    () => taskData?.items.find((item) => item.id === activeTaskId) ?? taskData?.items[0] ?? null,
    [activeTaskId, taskData?.items],
  );
  const submitMutation = useSubmitAnnotationTask(activeTask?.id ?? null);
  const activeEduStage = useMemo(() => resolveEduStage(activeTask), [activeTask]);
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

  useEffect(() => {
    if (activeTask && activeTask.id !== activeTaskId) {
      setActiveTaskId(activeTask.id);
    }
  }, [activeTask, activeTaskId]);

  useEffect(() => {
    if (!activeTask || !visibleCompetencies.length) {
      return;
    }
    form.setFieldsValue({
      confidence_level: 3,
      competencies: Object.fromEntries(visibleCompetencies.map((item) => [item.id, 0])),
    });
  }, [activeTask?.id, form, visibleCompetencies]);

  const handleClaim = async () => {
    if (!userId) {
      message.error("请先登录");
      return;
    }
    const result = await claimMutation.mutateAsync({
      annotator_user_id: userId,
      count: claimCount,
    });
    message.success(`已领取 ${result.claimed_count} 道题`);
  };

  const waitingCount =
    poolSummary?.items.find((item) => item.status === "WAITING")?.count ?? 0;

  const handleSubmit = async (values: AnnotationFormValues) => {
    if (!userId || !activeTask) {
      return;
    }
    const competencyValues = values.competencies ?? {};
    const competencyPayload = visibleCompetencies.map((item) => ({
      competency_id: item.id,
      level_value: competencyValues[item.id] ?? 0,
    }));
    const result = await submitMutation.mutateAsync({
      annotator_user_id: userId,
      cognitive_level_id: null,
      confidence_level: values.confidence_level ?? null,
      competencies: competencyPayload,
    });
    message.success(
      result.is_disputed
        ? "已提交，3 人标注存在分歧，题目进入待复核池"
        : `已提交，当前 ${result.annotation_count}/${result.required_annotations}`,
    );
    form.resetFields();
    setActiveTaskId(null);
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
                max={100}
                value={claimCount}
                onChange={(value: number | null) => setClaimCount(Number(value) || 1)}
              />
              <Button
                icon={<InboxOutlined />}
                onClick={handleClaim}
                loading={claimMutation.isPending}
              >
                领取题目
              </Button>
            </Space>
          }
        >
          <Typography.Text type="secondary">
            当前待标注池还有 {waitingCount} 道题，可自由选择本次领取数量。
          </Typography.Text>
          {!isLoading && !taskData?.items.length ? (
            <Empty description="暂无已领取任务，可从待标注池领取" />
          ) : (
            <List
              loading={isLoading}
              dataSource={taskData?.items ?? []}
              renderItem={(item: AnnotationTask) => (
                <List.Item
                  onClick={() => setActiveTaskId(item.id)}
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
                        <Tag icon={<ClockCircleOutlined />}>{item.task_status}</Tag>
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
            {activeTask ? (
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                <Space wrap>
                  <Tag color="blue">题目 #{activeTask.question_id}</Tag>
                  <Tag>{activeTask.question.subject.name}</Tag>
                  {activeTask.question.grade ? <Tag>{activeTask.question.grade.grade_name}</Tag> : null}
                  {activeTask.question.question_type ? (
                    <Tag>{activeTask.question.question_type.name}</Tag>
                  ) : null}
                  <Tag color="processing">
                    已提交 {activeTask.progress.submitted_annotation_count}/
                    {activeTask.progress.required_annotations}
                  </Tag>
                  <Tag color="purple">
                    并行中 {activeTask.progress.active_annotation_count}
                  </Tag>
                </Space>
                <Progress
                  percent={activeTask.progress.progress_percent}
                  size="small"
                  status="active"
                />
                <Typography.Text type="secondary">
                  当前题目支持多人并行标注，系统会实时同步标注进度；当达到 3 份及以上标注后，
                  会根据多数一致规则自动聚合，若无多数结论则进入争议复核。
                </Typography.Text>
                <QuestionRichText
                  html={activeTask.question.content?.stem_html}
                  text={activeTask.question.content?.stem_text}
                  emptyLabel="暂无题干"
                />
              </Space>
            ) : (
              <Empty description="请选择或领取一道题开始标注" />
            )}
          </Card>

          <Card title="提交标注">
            {!activeTask ? (
              <Alert type="info" showIcon message="领取任务后即可填写认知层级和核心素养矩阵。" />
            ) : (
              <Form form={form} layout="vertical" onFinish={handleSubmit}>
                <Form.Item name="confidence_level" label="信心等级">
                  <InputNumber min={1} max={5} style={{ width: 220 }} />
                </Form.Item>

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
                    </div>
                    );
                  })}
                </Space>

                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SendOutlined />}
                  loading={submitMutation.isPending}
                  style={{ marginTop: 16 }}
                >
                  提交标注
                </Button>
              </Form>
            )}
          </Card>
        </Space>
      </Col>
    </Row>
  );
}
