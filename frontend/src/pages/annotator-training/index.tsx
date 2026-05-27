import {
  BookOutlined,
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
  Drawer,
  Empty,
  Form,
  Progress,
  Radio,
  Row,
  Segmented,
  Select,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { formatBackendDateTime } from "@/app/date-time";
import { useAuthStore } from "@/app/store/auth-store";
import { CompetencyHelpPopover } from "@/components/competency-help-popover";
import { QuestionDetailSections } from "@/components/question-detail-sections";
import { QuestionRichText } from "@/components/question-rich-text";
import { useCompetencies, useQuestionDetail } from "@/modules/question-bank/hooks";
import {
  useSubmitTraining,
  useTrainingAttempts,
  useTrainingModule,
  useTrainingStatus,
} from "@/modules/training/hooks";
import type { CompetencyItem } from "@/types/dictionary";
import type {
  TrainingAttemptResponse,
  TrainingCompetencyDefinition,
  TrainingGuideExample,
  TrainingQuestion,
  TrainingQuestionCompetencyResult,
  TrainingQuestionResult,
  TrainingStage,
  TrainingSubmitResponse,
} from "@/types/training";

type TrainingFormValues = {
  answers?: Record<number, Record<number, number>>;
};

type TrainingPanelKey = "guide" | "practice" | "result";
type TrainingResultLike = TrainingAttemptResponse | TrainingSubmitResponse;

const LEVEL_LABELS = ["0级", "1级", "2级", "3级"];

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

function buildDefaultAnswerMap(
  questions: TrainingQuestion[],
  competencies: CompetencyItem[],
) {
  return Object.fromEntries(
    questions.map((question) => [
      question.question_id,
      Object.fromEntries(competencies.map((item) => [item.id, 0])),
    ]),
  ) as NonNullable<TrainingFormValues["answers"]>;
}

function resultToAttempt(result: TrainingSubmitResponse): TrainingAttemptResponse {
  return {
    stage: result.stage,
    passed: result.passed,
    score_percent: result.score_percent,
    pass_threshold: result.pass_threshold,
    attempt_no: result.attempt_no,
    completed_at: result.completed_at,
    question_results: result.question_results,
  };
}

function mergeAttemptAnswers(
  baseAnswers: NonNullable<TrainingFormValues["answers"]>,
  attempt: TrainingResultLike,
) {
  const nextAnswers = { ...baseAnswers };
  attempt.question_results.forEach((questionResult) => {
    const current = { ...(nextAnswers[questionResult.question_id] ?? {}) };
    questionResult.competency_results.forEach((item) => {
      current[item.competency_id] = item.selected_level;
    });
    nextAnswers[questionResult.question_id] = current;
  });
  return nextAnswers;
}

function formatAttemptTime(value: string) {
  return formatBackendDateTime(value);
}

export function AnnotatorTrainingPage() {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const location = useLocation();
  const session = useAuthStore((state) => state.session);
  const setSession = useAuthStore((state) => state.setSession);
  const userId = session?.id ?? null;
  const [stage, setStage] = useState<TrainingStage>("junior");
  const [activePanel, setActivePanel] = useState<TrainingPanelKey>("guide");
  const [answerDraft, setAnswerDraft] = useState<NonNullable<TrainingFormValues["answers"]>>({});
  const [latestResult, setLatestResult] = useState<TrainingSubmitResponse | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [practiceQuestionIds, setPracticeQuestionIds] = useState<number[] | null>(null);
  const [selectedAttemptNo, setSelectedAttemptNo] = useState<number | null>(null);
  const { data: status } = useTrainingStatus(userId);
  const { data: competencies } = useCompetencies();
  const { data: module, isLoading } = useTrainingModule(userId, stage);
  const { data: attempts = [] } = useTrainingAttempts(userId, stage);
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
  const reviewAttempts = useMemo(() => {
    const latestAttempt = latestResult ? resultToAttempt(latestResult) : null;
    const historicalAttempts = latestAttempt
      ? attempts.filter((item) => item.attempt_no !== latestAttempt.attempt_no)
      : attempts;
    return latestAttempt ? [latestAttempt, ...historicalAttempts] : historicalAttempts;
  }, [attempts, latestResult]);
  const selectedReviewAttempt =
    reviewAttempts.find((item) => item.attempt_no === selectedAttemptNo) ??
    reviewAttempts[0] ??
    null;
  const practiceQuestions = useMemo(() => {
    if (!module) return [];
    if (!practiceQuestionIds?.length) return module.questions;
    const idSet = new Set(practiceQuestionIds);
    return module.questions.filter((question) => idSet.has(question.question_id));
  }, [module, practiceQuestionIds]);
  const currentQuestion = practiceQuestions[currentQuestionIndex] ?? null;
  const currentQuestionResult = selectedReviewAttempt?.question_results.find(
    (item) => item.question_id === currentQuestion?.question_id,
  );
  const progressPercent = practiceQuestions.length
    ? Math.round(((currentQuestionIndex + 1) / practiceQuestions.length) * 100)
    : 0;
  const panelItems = [
    { label: "基础知识引导", value: "guide" },
    { label: "实战校准", value: "practice" },
    ...(reviewAttempts.length ? [{ label: "结果复盘", value: "result" }] : []),
  ];

  useEffect(() => {
    const state = location.state as { trainingRequired?: boolean; attemptedPath?: string } | null;
    if (!state?.trainingRequired) {
      return;
    }

    const targetLabel =
      state.attemptedPath === "/annotation-history" ? "我的标注记录" : "标注工作台";
    message.info(`请先完成培训准入，培训通过后才能进入${targetLabel}。`);
    navigate(location.pathname, { replace: true, state: null });
  }, [location.pathname, location.state, navigate]);

  useEffect(() => {
    if (!module || !visibleCompetencies.length) {
      return;
    }
    const initialAnswers = buildDefaultAnswerMap(module.questions, visibleCompetencies);
    form.setFieldsValue({
      answers: initialAnswers,
    });
    setAnswerDraft(initialAnswers);
    setCurrentQuestionIndex(0);
  }, [form, module, visibleCompetencies]);

  useEffect(() => {
    setActivePanel("guide");
    setCurrentQuestionIndex(0);
    setLatestResult(null);
    setPracticeQuestionIds(null);
    setSelectedAttemptNo(null);
  }, [stage]);

  useEffect(() => {
    if (!reviewAttempts.length) {
      setSelectedAttemptNo(null);
      return;
    }
    if (
      selectedAttemptNo === null ||
      !reviewAttempts.some((item) => item.attempt_no === selectedAttemptNo)
    ) {
      setSelectedAttemptNo(reviewAttempts[0].attempt_no);
    }
  }, [reviewAttempts, selectedAttemptNo]);

  const mergeCurrentAnswers = () => {
    const liveValues = form.getFieldsValue(true) as TrainingFormValues;
    const mergedAnswers = {
      ...answerDraft,
      ...(liveValues.answers ?? {}),
    };
    setAnswerDraft(mergedAnswers);
    return mergedAnswers;
  };

  const handleSubmit = async () => {
    if (!userId || !module) {
      return;
    }
    const answerValues = mergeCurrentAnswers();
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
    setSelectedAttemptNo(result.attempt_no);
    setPracticeQuestionIds(null);
    setActivePanel("result");
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
    if (!practiceQuestions.length) {
      return;
    }
    mergeCurrentAnswers();
    if (currentQuestionIndex >= practiceQuestions.length - 1) {
      void form.submit();
      return;
    }
    setCurrentQuestionIndex((value) => value + 1);
  };

  const resetPractice = (
    questionIds: number[] | null,
    answers: NonNullable<TrainingFormValues["answers"]>,
  ) => {
    form.setFieldsValue({ answers });
    setAnswerDraft(answers);
    setPracticeQuestionIds(questionIds);
    setCurrentQuestionIndex(0);
    setActivePanel("practice");
  };

  const handleRedoAll = () => {
    if (!module) return;
    resetPractice(null, buildDefaultAnswerMap(module.questions, visibleCompetencies));
  };

  const handleRedoWrong = (attempt: TrainingResultLike) => {
    if (!module) return;
    const wrongQuestionIds = attempt.question_results
      .filter((item) => !item.is_passed)
      .map((item) => item.question_id);
    if (!wrongQuestionIds.length) {
      message.info("这次记录没有错题，可以直接进入标注或选择全部重做。");
      return;
    }
    if (attempt.question_results.some((item) => !item.competency_results.length)) {
      message.warning("这次历史记录缺少逐素养答案明细，建议使用全部重做。");
      return;
    }
    const defaultAnswers = buildDefaultAnswerMap(module.questions, visibleCompetencies);
    resetPractice(wrongQuestionIds, mergeAttemptAnswers(defaultAnswers, attempt));
  };

  const canGoPrevious = currentQuestionIndex > 0;
  const isLastQuestion = practiceQuestions.length
    ? currentQuestionIndex === practiceQuestions.length - 1
    : false;

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card className="training-hero-card">
        <Space direction="vertical" size={14} style={{ width: "100%" }}>
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
            先用简明导学把素养边界和判题抓手理清，再进入单题校准。提交后会进入结果复盘页，逐题查看你的选择、标准答案和解释。
          </Typography.Paragraph>
          <Space wrap>
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
            <Segmented
              value={activePanel}
              options={panelItems}
              onChange={(value: string | number) => {
                setActivePanel(value as TrainingPanelKey);
              }}
            />
          </Space>
        </Space>
      </Card>

      {activePanel === "guide" ? (
        <KnowledgeGuide
          isLoading={isLoading}
          module={module}
          onStartPractice={() => setActivePanel("practice")}
        />
      ) : null}

      {activePanel === "practice" ? (
        <PracticePanel
          form={form}
          isLoading={isLoading}
          module={module}
          questions={practiceQuestions}
          currentQuestion={currentQuestion}
          currentQuestionIndex={currentQuestionIndex}
          currentQuestionResult={currentQuestionResult}
          visibleCompetencies={visibleCompetencies}
          competencyDefinitionMap={competencyDefinitionMap}
          progressPercent={progressPercent}
          canGoPrevious={canGoPrevious}
          isLastQuestion={isLastQuestion}
          isSubmitting={submitMutation.isPending}
          hasTrainingAccess={status?.training_scope !== "none"}
          onSubmit={handleSubmit}
          onValuesChange={(_, allValues) => {
            setAnswerDraft((current) => ({
              ...current,
              ...(allValues.answers ?? {}),
            }));
          }}
          onPrevious={() => setCurrentQuestionIndex((value) => Math.max(0, value - 1))}
          onFirst={() => setCurrentQuestionIndex(0)}
          onAdvance={handleAdvance}
        />
      ) : null}

      {activePanel === "result" ? (
        <ResultReviewPanel
          attempts={reviewAttempts}
          selectedAttemptNo={selectedAttemptNo}
          result={selectedReviewAttempt}
          module={module}
          onSelectAttempt={setSelectedAttemptNo}
          onRedoAll={handleRedoAll}
          onRedoWrong={handleRedoWrong}
          onGoAnnotate={() => navigate("/annotate")}
        />
      ) : null}
    </Space>
  );
}

function KnowledgeGuide({
  isLoading,
  module,
  onStartPractice,
}: {
  isLoading: boolean;
  module: ReturnType<typeof useTrainingModule>["data"];
  onStartPractice: () => void;
}) {
  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Card loading={isLoading}>
        {!module ? (
          <Empty description="暂无培训内容" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <div className="training-guide-stat">
                  <Typography.Text type="secondary">培训主题</Typography.Text>
                  <Typography.Title level={4}>{module.title}</Typography.Title>
                </div>
              </Col>
              <Col xs={24} md={8}>
                <div className="training-guide-stat">
                  <Typography.Text type="secondary">通过阈值</Typography.Text>
                  <Typography.Title level={4}>{module.pass_threshold}%</Typography.Title>
                </div>
              </Col>
              <Col xs={24} md={8}>
                <div className="training-guide-stat">
                  <Typography.Text type="secondary">实战题量</Typography.Text>
                  <Typography.Title level={4}>{module.required_question_count} 题</Typography.Title>
                </div>
              </Col>
            </Row>
            <Alert
              type="info"
              showIcon
              icon={<ReadOutlined />}
              message={module.summary}
              description="先看“这道题真正靠什么完成”，再决定哪些素养需要从 0 提升到 1/2/3。先抓主导动作，再看辅助支撑；默认 0 不是漏标，而是明确判断该素养不是本题重点。"
            />
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <GuideStep
                  title="第一眼：找核心动作"
                  text="先别急着逐项打分，先问自己：学生解这道题最关键的动作是什么，是抽象关系、计算变形、读图判断、建模转化，还是推理论证？"
                />
              </Col>
              <Col xs={24} lg={8}>
                <GuideStep
                  title="第二眼：分清主次"
                  text="一个素养只是出现，不代表就要给高层级。辅助理解或局部使用给 1 级，支撑关键步骤给 2 级，决定整题路径才给 3 级。"
                />
              </Col>
              <Col xs={24} lg={8}>
                <GuideStep
                  title="第三眼：敢于保留 0"
                  text="没有体现就保持 0。0 级会参与系统一致性投票，它不是空白，而是你明确判断“这道题不主要依赖这个素养”。"
                />
              </Col>
            </Row>
          </Space>
        )}
      </Card>

      {module ? (
        <>
          <Card title="素养地图">
            <Row gutter={[12, 12]}>
              {module.competency_definitions.map((item) => (
                <Col xs={24} md={12} xl={8} key={item.code}>
                  <div className="training-competency-card">
                    <CompetencyHelpPopover
                      name={item.name}
                      definition={item.definition}
                      focusTip={item.focus_tip}
                    />
                    <Typography.Paragraph type="secondary">
                      {item.definition}
                    </Typography.Paragraph>
                    <div className="training-focus-tip">{item.focus_tip}</div>
                    <TrainingBoundaryDetails item={item} />
                  </div>
                </Col>
              ))}
            </Row>
          </Card>

          <Card title="引导样例：先看专家怎么想">
            {!module.guide_examples.length ? (
              <Empty description="暂无引导样例" />
            ) : (
              <Row gutter={[16, 16]}>
                {module.guide_examples.map((example, index) => (
                  <Col xs={24} xl={12} key={example.question_id}>
                    <GuideExampleCard example={example} index={index} />
                  </Col>
                ))}
              </Row>
            )}
          </Card>

          <Card>
            <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
              <Space direction="vertical" size={4}>
                <Typography.Text strong>准备好了就进入实战校准</Typography.Text>
                <Typography.Text type="secondary">
                  系统会一次呈现一道题，最后提交后进入逐题复盘。
                </Typography.Text>
              </Space>
              <Button type="primary" icon={<RightOutlined />} onClick={onStartPractice}>
                进入实战校准
              </Button>
            </Space>
          </Card>
        </>
      ) : null}
    </Space>
  );
}

function GuideStep({ title, text }: { title: string; text: string }) {
  return (
    <div className="training-guide-step">
      <BookOutlined />
      <Typography.Text strong>{title}</Typography.Text>
      <Typography.Paragraph type="secondary">{text}</Typography.Paragraph>
    </div>
  );
}

function TrainingBoundaryDetails({ item }: { item: TrainingCompetencyDefinition }) {
  const groups = [
    { title: "适合标", values: item.positive_cues, color: "success" as const },
    { title: "谨慎标", values: item.negative_cues, color: "warning" as const },
    { title: "层级口径", values: item.level_guidance, color: "processing" as const },
    { title: "易混提醒", values: item.boundary_examples, color: "default" as const },
  ].filter((group) => group.values.length);

  if (!groups.length) {
    return null;
  }

  return (
    <div className="training-boundary-grid">
      {groups.map((group) => (
        <div key={group.title} className="training-boundary-block">
          <Tag color={group.color}>{group.title}</Tag>
          <ul>
            {group.values.map((value) => (
              <li key={value}>{value}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function TrainingQuestionPreview({ question }: { question: TrainingQuestion }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const detailQuery = useQuestionDetail(detailOpen ? question.question_id : null);

  return (
    <>
      <div className="training-question-preview">
        <Space direction="vertical" size={10} style={{ width: "100%" }}>
          <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
            <Typography.Text type="secondary">
              预览仅展示题干摘要，含子题或完整解析请打开详情。
            </Typography.Text>
            <Button size="small" onClick={() => setDetailOpen(true)}>
              查看题目详情
            </Button>
          </Space>
          <QuestionRichText
            text={question.stem_text}
            emptyLabel="暂无题干"
            className="question-rich-text--training-preview"
          />
        </Space>
      </div>
      <Drawer
        title={`题目详情 #${question.question_id}`}
        width="min(980px, 92vw)"
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        destroyOnClose
      >
        {detailQuery.data ? (
          <QuestionDetailSections detail={detailQuery.data} />
        ) : (
          <Empty description={detailQuery.isLoading ? "题目详情加载中" : "暂无题目详情"} />
        )}
      </Drawer>
    </>
  );
}

function PracticePanel({
  form,
  isLoading,
  module,
  questions,
  currentQuestion,
  currentQuestionIndex,
  currentQuestionResult,
  visibleCompetencies,
  competencyDefinitionMap,
  progressPercent,
  canGoPrevious,
  isLastQuestion,
  isSubmitting,
  hasTrainingAccess,
  onSubmit,
  onValuesChange,
  onPrevious,
  onFirst,
  onAdvance,
}: {
  form: ReturnType<typeof Form.useForm>[0];
  isLoading: boolean;
  module: ReturnType<typeof useTrainingModule>["data"];
  questions: TrainingQuestion[];
  currentQuestion: TrainingQuestion | null;
  currentQuestionIndex: number;
  currentQuestionResult?: TrainingQuestionResult;
  visibleCompetencies: CompetencyItem[];
  competencyDefinitionMap: Map<string, { definition: string; focus_tip: string }>;
  progressPercent: number;
  canGoPrevious: boolean;
  isLastQuestion: boolean;
  isSubmitting: boolean;
  hasTrainingAccess: boolean;
  onSubmit: () => void;
  onValuesChange: (_: Partial<TrainingFormValues>, allValues: TrainingFormValues) => void;
  onPrevious: () => void;
  onFirst: () => void;
  onAdvance: () => void;
}) {
  return (
    <Card
      title="实战校准"
      loading={isLoading}
      extra={
        hasTrainingAccess ? (
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
        <Form form={form} layout="vertical" onFinish={onSubmit} onValuesChange={onValuesChange}>
          <Space direction="vertical" size={18} style={{ width: "100%" }}>
            <div className="training-practice-progress">
              <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
                <Typography.Text strong>
                  第 {currentQuestionIndex + 1} / {questions.length} 题
                </Typography.Text>
                <Typography.Text type="secondary">
                  当前页答案会自动保留，最后一题统一提交
                </Typography.Text>
              </Space>
              <Progress percent={progressPercent} size="small" status="active" />
              <Steps
                size="small"
                current={currentQuestionIndex}
                items={questions.map((question, index) => ({
                  title: `题${index + 1}`,
                  status: currentQuestionResult
                    ? latestStepStatus(question.question_id, questions, index, currentQuestionIndex)
                    : index < currentQuestionIndex
                      ? "finish"
                      : index === currentQuestionIndex
                        ? "process"
                        : "wait",
                }))}
              />
            </div>

            <div className="training-question-panel">
              <Space direction="vertical" size={14} style={{ width: "100%" }}>
                <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
                  <Typography.Title level={4} style={{ margin: 0 }}>
                    校准题 #{currentQuestion.question_id}
                  </Typography.Title>
                  <Space wrap>
                    <Tag>{currentQuestion.subject_name}</Tag>
                    {currentQuestion.grade_name ? <Tag>{currentQuestion.grade_name}</Tag> : null}
                    {currentQuestion.question_type_name ? (
                      <Tag>{currentQuestion.question_type_name}</Tag>
                    ) : null}
                  </Space>
                </Space>
                <TrainingQuestionPreview question={currentQuestion} />
                {currentQuestion.coach_tip ? (
                  <Alert type="info" showIcon message={currentQuestion.coach_tip} />
                ) : null}
                <div className="training-answer-grid">
                  {visibleCompetencies.map((item) => {
                    const definition = competencyDefinitionMap.get(item.code);
                    return (
                      <div
                        key={`${currentQuestion.question_id}-${item.id}`}
                        className="training-answer-row"
                      >
                        <CompetencyHelpPopover
                          name={item.name}
                          definition={definition?.definition}
                          focusTip={definition?.focus_tip}
                        />
                        <Form.Item
                          name={["answers", currentQuestion.question_id, item.id]}
                          noStyle
                          preserve
                        >
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
                </div>
                {currentQuestionResult ? (
                  <QuestionResultAlert result={currentQuestionResult} />
                ) : null}
              </Space>
            </div>

            <Space style={{ justifyContent: "space-between", width: "100%" }} wrap>
              <Button icon={<LeftOutlined />} disabled={!canGoPrevious} onClick={onPrevious}>
                上一题
              </Button>
              <Space wrap>
                <Button onClick={onFirst}>回到第一题</Button>
                <Button
                  type="primary"
                  icon={isLastQuestion ? <SendOutlined /> : <RightOutlined />}
                  loading={isSubmitting}
                  onClick={onAdvance}
                >
                  {isLastQuestion ? "提交培训考核" : "保存并进入下一题"}
                </Button>
              </Space>
            </Space>
          </Space>
        </Form>
      )}
    </Card>
  );
}

function latestStepStatus(
  questionId: number,
  questions: TrainingQuestion[],
  index: number,
  currentQuestionIndex: number,
) {
  const current = questions[currentQuestionIndex];
  if (current?.question_id === questionId) return "process" as const;
  return index < currentQuestionIndex ? "finish" as const : "wait" as const;
}

function ResultReviewPanel({
  attempts,
  selectedAttemptNo,
  result,
  module,
  onSelectAttempt,
  onRedoAll,
  onRedoWrong,
  onGoAnnotate,
}: {
  attempts: TrainingResultLike[];
  selectedAttemptNo: number | null;
  result: TrainingResultLike | null;
  module: ReturnType<typeof useTrainingModule>["data"];
  onSelectAttempt: (attemptNo: number) => void;
  onRedoAll: () => void;
  onRedoWrong: (attempt: TrainingResultLike) => void;
  onGoAnnotate: () => void;
}) {
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);
  const activeResult = result?.question_results.find(
    (item) => item.question_id === (activeQuestionId ?? result.question_results[0]?.question_id),
  );
  const activeQuestion = module?.questions.find(
    (item) => item.question_id === activeResult?.question_id,
  );

  useEffect(() => {
    setActiveQuestionId(result?.question_results[0]?.question_id ?? null);
  }, [result]);

  if (!result) {
    return (
      <Card>
        <Empty description="提交培训后会显示结果复盘" />
      </Card>
    );
  }

  const wrongCount = result.question_results.filter((item) => !item.is_passed).length;

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Alert
        type={result.passed ? "success" : "warning"}
        showIcon
        message={
          result.passed
            ? `本次培训通过，得分 ${result.score_percent}%`
            : `本次培训未通过，得分 ${result.score_percent}%`
        }
        description={
          result.passed
            ? "你已经获得对应学段的正式标注权限。建议先看一遍复盘，确认自己的判断边界。"
            : "先看失分题的标准层级和解释，再回到实战校准重新练习。"
        }
        action={
          <Space wrap>
            <Button onClick={onRedoAll}>全部重做</Button>
            <Button disabled={!wrongCount} onClick={() => onRedoWrong(result)}>
              错题重做{wrongCount ? `（${wrongCount}题）` : ""}
            </Button>
            {result.passed ? (
              <Button type="primary" onClick={onGoAnnotate}>
                进入标注工作台
              </Button>
            ) : null}
          </Space>
        }
      />

      <Card>
        <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
          <Space direction="vertical" size={4}>
            <Typography.Text strong>选择复盘记录</Typography.Text>
            <Typography.Text type="secondary">
              默认展示最新一次记录；可以切换任意一次答题记录，并基于该记录重做全部题或只重做错题。
            </Typography.Text>
          </Space>
          <Select
            style={{ minWidth: 320 }}
            value={selectedAttemptNo ?? result.attempt_no}
            onChange={onSelectAttempt}
            options={attempts.map((attempt) => ({
              value: attempt.attempt_no,
              label: `第 ${attempt.attempt_no} 次 · ${attempt.score_percent}% · ${
                attempt.passed ? "通过" : "未通过"
              } · ${formatAttemptTime(attempt.completed_at)}`,
            }))}
          />
        </Space>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={7}>
          <Card title="题目得分">
            <Space direction="vertical" size={10} style={{ width: "100%" }}>
              {result.question_results.map((item, index) => (
                <button
                  key={item.question_id}
                  type="button"
                  className={`training-result-pill${
                    item.question_id === activeResult?.question_id
                      ? " training-result-pill--active"
                      : ""
                  }`}
                  onClick={() => setActiveQuestionId(item.question_id)}
                >
                  <span>第 {index + 1} 题</span>
                  <span>{item.score_percent}%</span>
                  <Tag color={item.is_passed ? "success" : "warning"}>
                    {item.is_passed ? "通过" : "需复习"}
                  </Tag>
                </button>
              ))}
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={17}>
          <Card title="逐题复盘">
            {activeResult && activeQuestion ? (
              <Space direction="vertical" size={16} style={{ width: "100%" }}>
                <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
                  <Typography.Title level={4} style={{ margin: 0 }}>
                    校准题 #{activeQuestion.question_id}
                  </Typography.Title>
                  <Space wrap>
                    <Tag>{activeQuestion.subject_name}</Tag>
                    {activeQuestion.grade_name ? <Tag>{activeQuestion.grade_name}</Tag> : null}
                    <Tag color={activeResult.is_passed ? "success" : "warning"}>
                      {activeResult.score_percent}%
                    </Tag>
                  </Space>
                </Space>
                <TrainingQuestionPreview question={activeQuestion} />
                <QuestionResultAlert result={activeResult} />
                {activeQuestion.review_analysis ? (
                  <ResultTextBlock title="标注解析" text={activeQuestion.review_analysis} />
                ) : null}
                <CompetencyComparisonList items={activeResult.competency_results} />
                {activeQuestion.answer_text ? (
                  <ResultTextBlock title="参考答案" text={activeQuestion.answer_text} />
                ) : null}
                {activeQuestion.solution_text ? (
                  <ResultTextBlock title="解题说明" text={activeQuestion.solution_text} />
                ) : null}
              </Space>
            ) : (
              <Empty description="请选择一道题查看复盘" />
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  );
}

function CompetencyComparisonList({
  items,
}: {
  items: TrainingQuestionCompetencyResult[];
}) {
  return (
    <Space direction="vertical" size={10} style={{ width: "100%" }}>
      {items.map((item) => {
        const shouldExplain = item.expected_level > 0 || item.selected_level > 0 || !item.is_match;
        if (!shouldExplain) return null;
        return (
          <div
            key={item.competency_id}
            className={`training-comparison-row${
              item.is_match ? " training-comparison-row--match" : ""
            }`}
          >
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
                <Typography.Text strong>{item.competency_name}</Typography.Text>
                <Space wrap>
                  <Tag color={item.is_match ? "success" : "error"}>
                    你选 {LEVEL_LABELS[item.selected_level]}
                  </Tag>
                  <Tag color="processing">标准 {LEVEL_LABELS[item.expected_level]}</Tag>
                </Space>
              </Space>
              <Typography.Text type="secondary">{item.level_reason}</Typography.Text>
              <Typography.Text type="secondary">{item.focus_tip}</Typography.Text>
            </Space>
          </div>
        );
      })}
    </Space>
  );
}

function ResultTextBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className="training-result-text-block">
      <Typography.Text strong>{title}</Typography.Text>
      <QuestionRichText text={text} emptyLabel="暂无内容" />
    </div>
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
    <div className="training-example-card">
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        <Space wrap style={{ justifyContent: "space-between", width: "100%" }}>
          <Typography.Text strong>引导样例 {index + 1}</Typography.Text>
          <Space wrap>
            <Tag>{example.subject_name}</Tag>
            {example.grade_name ? <Tag>{example.grade_name}</Tag> : null}
            {example.question_type_name ? <Tag>{example.question_type_name}</Tag> : null}
          </Space>
        </Space>
        <QuestionRichText text={example.stem_text} emptyLabel="暂无题干" />
        <Alert type="success" showIcon message={example.coach_tip} />
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          {example.competencies.map((item) => (
            <div key={`${example.question_id}-${item.competency_id}`} className="training-example-reason">
              <Space wrap>
                <CompetencyHelpPopover
                  name={item.competency_name}
                  definition={item.definition}
                  focusTip={item.focus_tip}
                />
                <Tag color="processing">建议层级 L{item.level_value}</Tag>
              </Space>
              <Typography.Text type="secondary">{item.level_reason}</Typography.Text>
            </div>
          ))}
        </Space>
        {example.answer_text ? <ResultTextBlock title="参考答案" text={example.answer_text} /> : null}
        {example.solution_text ? <ResultTextBlock title="解题提示" text={example.solution_text} /> : null}
      </Space>
    </div>
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
