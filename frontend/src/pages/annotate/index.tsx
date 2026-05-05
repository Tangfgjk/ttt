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
  Radio,
  Row,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";

import { useAuthStore } from "@/app/store/auth-store";
import { QuestionRichText } from "@/components/question-rich-text";
import {
  useAnnotationTasks,
  useClaimAnnotationTasks,
  useSubmitAnnotationTask,
} from "@/modules/annotations/hooks";
import { useCompetencies } from "@/modules/question-bank/hooks";
import type { AnnotationTask } from "@/types/annotations";

type AnnotationFormValues = {
  confidence_level?: number;
  competencies?: Record<number, number>;
};

export function AnnotatePage() {
  const [form] = Form.useForm();
  const session = useAuthStore((state) => state.session);
  const userId = session?.id ?? null;
  const { data: taskData, isLoading } = useAnnotationTasks(userId, "IN_PROGRESS");
  const { data: competencies } = useCompetencies();
  const claimMutation = useClaimAnnotationTasks();
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const activeTask = useMemo(
    () => taskData?.items.find((item) => item.id === activeTaskId) ?? taskData?.items[0] ?? null,
    [activeTaskId, taskData?.items],
  );
  const submitMutation = useSubmitAnnotationTask(activeTask?.id ?? null);

  useEffect(() => {
    if (activeTask && activeTask.id !== activeTaskId) {
      setActiveTaskId(activeTask.id);
    }
  }, [activeTask, activeTaskId]);

  useEffect(() => {
    if (!activeTask || !competencies?.length) {
      return;
    }
    form.setFieldsValue({
      confidence_level: 3,
      competencies: Object.fromEntries(competencies.map((item) => [item.id, 0])),
    });
  }, [activeTask?.id, competencies, form]);

  const handleClaim = async () => {
    if (!userId) {
      message.error("请先登录");
      return;
    }
    const result = await claimMutation.mutateAsync({
      annotator_user_id: userId,
      count: 10,
    });
    message.success(`已领取 ${result.claimed_count} 道题`);
  };

  const handleSubmit = async (values: AnnotationFormValues) => {
    if (!userId || !activeTask) {
      return;
    }
    const competencyPayload = Object.entries(values.competencies ?? {}).map(
      ([competencyId, levelValue]) => ({
        competency_id: Number(competencyId),
        level_value: levelValue,
      }),
    );
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
            <Button
              icon={<InboxOutlined />}
              onClick={handleClaim}
              loading={claimMutation.isPending}
            >
              领取 10 道
            </Button>
          }
        >
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
                </Space>
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
                  {(competencies ?? []).map((item) => (
                    <div key={item.id} className="matrix-row">
                      <Typography.Text strong>{item.name}</Typography.Text>
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
                  ))}
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
