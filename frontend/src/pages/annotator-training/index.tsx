import {
  CheckCircleOutlined,
  LeftOutlined,
  ReadOutlined,
  RightOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Progress,
  Radio,
  Row,
  Segmented,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/app/store/auth-store";
import { CompetencyHelpPopover } from "@/components/competency-help-popover";
import { QuestionRichText } from "@/components/question-rich-text";
import { useCompetencies } from "@/modules/question-bank/hooks";
import { useSubmitTraining, useTrainingModule, useTrainingStatus } from "@/modules/training/hooks";
import type { CompetencyItem } from "@/types/dictionary";
import type {
  TrainingGuideExample,
  TrainingQuestion,
  TrainingQuestionResult,
  TrainingStage,
  TrainingSubmitResponse,
} from "@/types/training";

type TrainingFormValues = {
  answers?: Record<number, Record<number, number>>;
};

function scopeLabel(scope: string) {
  if (scope === "both") return "已通过初中 / 高中培训";
  if (scope === "junior") return "已通过初中培训";
  if (scope === "senior") return "已通过高中培训";
  return "未完成培训";
}

function filterCompetencies(
  items: CompetencyItem[] | undefined,
  codes: string[] | undefined,
) {
  if (!items?.length || !codes?.length) {
    return [];
  }
  const codeSet = new Set(codes);
  return items.filter((item) => codeSet.has(item.code));
}

export function AnnotatorTrainingPage() {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const session = useAuthStore((state) => state.session);
  const setSession = useAuthStore((state) => state.setSession);
  const userId = session?.id ?? null;
  const [stage, setStage] = useState<TrainingStage>("junior");
  const [latestResult, setLatestResult] = useState<TrainingSubmitResponse | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const { data: status } = useTrainingStatus(userId);
  const { data: competencies } = useCompetencies();
  const { data: module, isLoading } = useTrainingModule(userId, stage);
  const submitMutation = useSubmitTraining();

  const visibleCompetencies = useMemo(
    () =>
      filterCompetencies(
        competencies,
        module?.competency_definitions.map((item) => item.code),
      ),
    [competencies, module?.competency_definitions],
  );
  const competencyDefinitionMap = useMemo(
    () =>
      new Map(module?.competency_definitions.map((item) => [item.code, item]) ?? []),
    [module?.competency_definitions],
  );
  const currentQuestion = module?.questions[currentQuestionIndex] ?? null;
  const currentQuestionResult = latestResult?.question_results.find(
    (item) => item.question_id === currentQuestion?.question_id,
  );
  const progressPercent = module?.questions.length
    ? Math.round(((currentQuestionIndex + 1) / module.questions.length) * 100)
    : 0;

  useEffect(() => {
    if (!module || !visibleCompetencies.length) {
      return;
    }
    form.setFieldsValue({
      answers: Object.fromEntries(
        module.questions.map((question) => [
          question.question_id,
          Object.fromEntries(visibleCompetencies.map((item) => [item.id, 0])),
        ]),
      ),
    });
    setCurrentQuestionIndex(0);
  }, [form, module, visibleCompetencies]);

  useEffect(() => {
    setCurrentQuestionIndex(0);
    setLatestResult(null);
  }, [stage]);

  const handleSubmit = async (values: TrainingFormValues) => {
    if (!userId || !module) {
      return;
    }
    const answerValues = values.answers ?? {};
    const result = await submitMutation.mutateAsync({
      user_id: userId,
      stage,
      answers: module.questions.map((question) => ({
        question_id: question.question_id,
        competencies: visibleCompetencies.map((item) => ({
          competency_id: item.id,
          level_value: answerValues[question.question_id]?.[item.id] ?? 0,
        })),
      })),
    });
    setLatestResult(result);
    if (session) {
      setSession({
        ...session,
        trainingScope: result.training_scope,
      });
    }
    message.success(
      result.passed
        ? `培训通过，得分 ${result.score_percent}%`
        : `培训未通过，得分 ${result.score_percent}%`,
    );
  };

  const handleAdvance = () => {
    if (!module) {
      return;
    }
    if (currentQuestionIndex >= module.questions.length - 1) {
      void form.submit();
      return;
    }
    setCurrentQuestionIndex((value) => value + 1);
  };

  const canGoPrevious = currentQuestionIndex > 0;
  const isLastQuestion = module ? currentQuestionIndex === module.questions.length - 1 : false;

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Space wrap>
            <Tag color={status?.training_scope === "none" ? "default" : "green"}>
              {scopeLabel(status?.training_scope ?? session?.trainingScope ?? "none")}
            </Tag>
            {status?.junior_completed ? <Tag color="blue">初中可标注</Tag> : null}
            {status?.senior_completed ? <Tag color="purple">高中可标注</Tag> : null}
          </Space>
          <Typography.Title level={3} style={{ margin: 0 }}>
            标注员培训与准入
          </Typography.Title>
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            培训分为“素养定义学习 + 引导样例 + 单题实战校准”。先理解每个素养的边界，再一题一题完成校准考核，通过后系统会自动开放对应学段的正式标注权限。
          </Typography.Paragraph>
          <Segmented
            value={stage}
            options={[
              { label: "初中培训", value: "junior" },
              { label: "高中培训", value: "senior" },
            ]}
            onChange={(value: string | number) => {
              setStage(value as TrainingStage);
            }}
          />
        </Space>
      </Card>

      {latestResult ? (
        <Alert
          type={latestResult.passed ? "success" : "warning"}
          showIcon
          message={
            latestResult.passed
              ? `本次培训通过，得分 ${latestResult.score_percent}%`
              : `本次培训未通过，得分 ${latestResult.score_percent}%`
          }
          description={
            latestResult.passed ? (
              <Button type="link" style={{ paddingLeft: 0 }} onClick={() => navigate("/annotate")}>
                进入标注工作台
              </Button>
            ) : (
              "你可以先回看左侧学习要点与引导样例，再定位到失分题重新理解判断边界。"
            )
          }
        />
      ) : null}

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}>
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Card title="培训导学" loading={isLoading}>
              {!module ? (
                <Empty description="暂无培训内容" />
              ) : (
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Descriptions column={1} size="small" bordered>
                    <Descriptions.Item label="培训主题">{module.title}</Descriptions.Item>
                    <Descriptions.Item label="通过阈值">{module.pass_threshold}%</Descriptions.Item>
                    <Descriptions.Item label="考核题量">{module.required_question_count} 题</Descriptions.Item>
                  </Descriptions>
                  <Alert type="info" showIcon icon={<ReadOutlined />} message={module.summary} />
                  <Typography.Text type="secondary">
                    培训题和正式标注页里，把鼠标悬停在素养名称上就能随时查看定义、识别提示和 0-3 级说明。
                  </Typography.Text>
                </Space>
              )}
            </Card>

            <Card title="素养速查" loading={isLoading}>
              {!module ? (
                <Empty description="暂无素养定义" />
              ) : (
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  {module.competency_definitions.map((item) => (
                    <Card key={item.code} size="small">
                      <Space direction="vertical" size={8} style={{ width: "100%" }}>
                        <CompetencyHelpPopover
                          name={item.name}
                          definition={item.definition}
                          focusTip={item.focus_tip}
                        />
                        <Typography.Text type="secondary">{item.definition}</Typography.Text>
                        <Tag color="processing">{item.focus_tip}</Tag>
                      </Space>
                    </Card>
                  ))}
                </Space>
              )}
            </Card>

            <Card title="引导样例" loading={isLoading}>
              {!module?.guide_examples.length ? (
                <Empty description="暂无引导样例" />
              ) : (
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  {module.guide_examples.map((example, index) => (
                    <GuideExampleCard key={example.question_id} example={example} index={index} />
                  ))}
                </Space>
              )}
            </Card>

            {latestResult ? (
              <Card title="本次校准结果">
                <Space direction="vertical" size={10} style={{ width: "100%" }}>
                  {latestResult.question_results.map((item, index) => (
                    <Button
                      key={item.question_id}
                      block
                      type={item.question_id === currentQuestion?.question_id ? "primary" : "default"}
                      onClick={() => setCurrentQuestionIndex(index)}
                    >
                      第 {index + 1} 题 · {item.score_percent}% · {item.is_passed ? "通过" : "需复习"}
                    </Button>
                  ))}
                </Space>
              </Card>
            ) : null}
          </Space>
        </Col>

        <Col xs={24} xl={15}>
          <Card
            title="实战校准"
            extra={
              status?.training_scope !== "none" ? (
                <Tag icon={<CheckCircleOutlined />} color="success">
                  已有培训权限
                </Tag>
              ) : (
                <Tag icon={<SafetyCertificateOutlined />}>待通过</Tag>
              )
            }
          >
            {!module || !currentQuestion ? (
              <Empty description="暂无可用培训题，请先确认金标数据已导入。" />
            ) : (
              <Form form={form} layout="vertical" onFinish={handleSubmit}>
                <Space direction="vertical" size={18} style={{ width: "100%" }}>
                  <Card size="small">
                    <Space direction="vertical" size={12} style={{ width: "100%" }}>
                      <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
                        <Typography.Text strong>
                          第 {currentQuestionIndex + 1} / {module.questions.length} 题
                        </Typography.Text>
                        <Typography.Text type="secondary">
                          一次只做一道题，当前页答案会自动保留
                        </Typography.Text>
                      </Space>
                      <Progress percent={progressPercent} size="small" status="active" />
                      <Steps
                        size="small"
                        current={currentQuestionIndex}
                        items={module.questions.map((question, index) => ({
                          title: `题${index + 1}`,
                          status: latestResult
                            ? latestResult.question_results.find(
                                (item) => item.question_id === question.question_id,
                              )?.is_passed
                              ? "finish"
                              : "error"
                            : index < currentQuestionIndex
                              ? "finish"
                              : index === currentQuestionIndex
                                ? "process"
                                : "wait",
                        }))}
                      />
                    </Space>
                  </Card>

                  <Card
                    type="inner"
                    title={`校准题 #${currentQuestion.question_id}`}
                    extra={
                      <Space wrap>
                        <Tag>{currentQuestion.subject_name}</Tag>
                        {currentQuestion.grade_name ? <Tag>{currentQuestion.grade_name}</Tag> : null}
                        {currentQuestion.question_type_name ? (
                          <Tag>{currentQuestion.question_type_name}</Tag>
                        ) : null}
                      </Space>
                    }
                  >
                    <Space direction="vertical" size={14} style={{ width: "100%" }}>
                      <QuestionRichText text={currentQuestion.stem_text} emptyLabel="暂无题干" />
                      {visibleCompetencies.map((item) => {
                        const definition = competencyDefinitionMap.get(item.code);
                        return (
                          <div key={`${currentQuestion.question_id}-${item.id}`} className="matrix-row">
                            <CompetencyHelpPopover
                              name={item.name}
                              definition={definition?.definition}
                              focusTip={definition?.focus_tip}
                            />
                            <Form.Item name={["answers", currentQuestion.question_id, item.id]} noStyle>
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
                      {currentQuestionResult ? (
                        <QuestionResultAlert result={currentQuestionResult} />
                      ) : null}
                    </Space>
                  </Card>

                  <Space style={{ justifyContent: "space-between", width: "100%" }} wrap>
                    <Button
                      icon={<LeftOutlined />}
                      disabled={!canGoPrevious}
                      onClick={() => setCurrentQuestionIndex((value) => Math.max(0, value - 1))}
                    >
                      上一题
                    </Button>
                    <Space wrap>
                      <Button onClick={() => setCurrentQuestionIndex(0)}>回到第一题</Button>
                      <Button
                        type="primary"
                        icon={isLastQuestion ? <SendOutlined /> : <RightOutlined />}
                        loading={submitMutation.isPending}
                        onClick={handleAdvance}
                      >
                        {isLastQuestion ? "提交培训考核" : "保存并进入下一题"}
                      </Button>
                    </Space>
                  </Space>
                </Space>
              </Form>
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

function GuideExampleCard({
  example,
  index,
}: {
  example: TrainingGuideExample;
  index: number;
}) {
  return (
    <Card
      size="small"
      title={`引导样例 ${index + 1}`}
      extra={
        <Space wrap>
          <Tag>{example.subject_name}</Tag>
          {example.grade_name ? <Tag>{example.grade_name}</Tag> : null}
          {example.question_type_name ? <Tag>{example.question_type_name}</Tag> : null}
        </Space>
      }
    >
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <QuestionRichText text={example.stem_text} emptyLabel="暂无题干" />
        <Alert type="success" showIcon message={example.coach_tip} />
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          {example.competencies.map((item) => (
            <Card key={`${example.question_id}-${item.competency_id}`} size="small">
              <Space direction="vertical" size={6} style={{ width: "100%" }}>
                <Space wrap>
                  <CompetencyHelpPopover
                    name={item.competency_name}
                    definition={item.definition}
                    focusTip={item.focus_tip}
                  />
                  <Tag color="processing">建议层级 L{item.level_value}</Tag>
                </Space>
                <Typography.Text type="secondary">{item.level_reason}</Typography.Text>
                <Tag>{item.focus_tip}</Tag>
              </Space>
            </Card>
          ))}
        </Space>
        {example.answer_text ? (
          <div>
            <Typography.Text strong>参考答案</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 0 }}>
              {example.answer_text}
            </Typography.Paragraph>
          </div>
        ) : null}
        {example.solution_text ? (
          <div>
            <Typography.Text strong>解题提示</Typography.Text>
            <Typography.Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 0 }}>
              {example.solution_text}
            </Typography.Paragraph>
          </div>
        ) : null}
      </Space>
    </Card>
  );
}

function QuestionResultAlert({ result }: { result: TrainingQuestionResult }) {
  return (
    <Alert
      type={result.is_passed ? "success" : "warning"}
      showIcon
      message={`期望素养：${result.expected_competency_names.join("、") || "无"}`}
      description={`你的选择：${result.predicted_competency_names.join("、") || "无"}；本题得分 ${result.score_percent}%`}
    />
  );
}
