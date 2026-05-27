import {
  ExclamationCircleOutlined,
  InboxOutlined,
  LockOutlined,
  SendOutlined,
  SyncOutlined,
  UnlockOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Radio,
  Result,
  Row,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";

import { formatBackendDateTime } from "@/app/date-time";
import { useAuthStore } from "@/app/store/auth-store";
import { QuestionDetailSections } from "@/components/question-detail-sections";
import { QuestionRichText } from "@/components/question-rich-text";
import { annotationStatusLabelMap } from "@/constants/annotation-status";
import {
  useAnnotationPoolSummary,
  useAutoReconcileReviewTasks,
  useClaimReviewTasks,
  useReviewTasks,
  useSubmitReviewTask,
} from "@/modules/annotations/hooks";
import { useCompetencies, useQuestionDetail } from "@/modules/question-bank/hooks";
import type { ReviewTask } from "@/types/annotations";
import type { CompetencyItem } from "@/types/dictionary";

type ReviewFormValues = {
  competencies?: Record<number, number>;
  review_comment?: string;
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

function resolveEduStage(task: ReviewTask | null) {
  const grade = task?.question.grade;
  if (grade?.edu_stage) return grade.edu_stage;
  const gradeIndex = grade?.grade_index;
  if (gradeIndex && gradeIndex >= 7 && gradeIndex <= 9) return "junior";
  if (gradeIndex && gradeIndex >= 10 && gradeIndex <= 12) return "senior";
  return null;
}

function filterCompetenciesByStage(
  items: CompetencyItem[] | undefined,
  eduStage: string | null,
) {
  if (!items?.length) return [];
  if (eduStage === "junior") return items.filter((item) => JUNIOR_COMPETENCY_CODES.has(item.code));
  if (eduStage === "senior") return items.filter((item) => SENIOR_COMPETENCY_CODES.has(item.code));
  return items;
}

function confidenceLevelMeta(level?: number | null) {
  if (level == null) return { label: "-", color: "default" as const };
  if (level >= 5) return { label: "高", color: "red" as const };
  if (level >= 3) return { label: "中", color: "gold" as const };
  return { label: "低", color: "blue" as const };
}

function competencyLevelTagColor(levelValue: number) {
  if (levelValue >= 3) return "magenta";
  if (levelValue === 2) return "purple";
  if (levelValue === 1) return "processing";
  return "default";
}

function getConsensusStatusLabel(status: string) {
  if (status === "DISPUTED") return "存在分歧";
  if (status === "CONSENSUS") return "已达成一致";
  if (status === "PENDING") return "待处理";
  return status;
}

export function ReviewPage() {
  const [form] = Form.useForm();
  const session = useAuthStore((state) => state.session);
  const reviewerId = session?.id ?? null;
  const [activeTaskId, setActiveTaskId] = useState<number | null>(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [unlockedCompetencyIds, setUnlockedCompetencyIds] = useState<number[]>([]);
  const { data: taskData, isLoading } = useReviewTasks(reviewerId, "IN_PROGRESS");
  const { data: poolSummary } = useAnnotationPoolSummary();
  const { data: competencies } = useCompetencies();
  const claimMutation = useClaimReviewTasks();
  const reconcileMutation = useAutoReconcileReviewTasks();
  const activeTask = useMemo(
    () => taskData?.items.find((item) => item.id === activeTaskId) ?? taskData?.items[0] ?? null,
    [activeTaskId, taskData?.items],
  );
  const submitMutation = useSubmitReviewTask(activeTask?.id ?? null);
  const questionDetailQuery = useQuestionDetail(detailDrawerOpen ? (activeTask?.question_id ?? null) : null);
  const activeEduStage = useMemo(() => resolveEduStage(activeTask), [activeTask]);
  const visibleCompetencies = useMemo(
    () => filterCompetenciesByStage(competencies, activeEduStage),
    [activeEduStage, competencies],
  );
  const isV10ReviewTask = useMemo(
    () =>
      activeTask?.review_logs.some(
        (log) =>
          log.action_code === "AUTO_REVIEW_CREATED" &&
          log.detail_json?.decision_version === "V10",
      ) ?? false,
    [activeTask],
  );
  const rawDisagreedCompetencyIds = useMemo(() => {
    const levelSets = new Map<number, Set<number>>();
    activeTask?.annotations.forEach((annotation) => {
      annotation.competencies.forEach((item) => {
        const levels = levelSets.get(item.competency_id) ?? new Set<number>();
        levels.add(item.level_value);
        levelSets.set(item.competency_id, levels);
      });
    });
    return new Set(
      [...levelSets.entries()]
        .filter(([, levels]) => levels.size > 1)
        .map(([competencyId]) => competencyId),
    );
  }, [activeTask]);
  const disputedCompetencyIds = useMemo(
    () => {
      const ids =
        activeTask?.consensus.dimensions
          .filter(
            (item) =>
              item.dimension_type === "competency" &&
              item.consensus_status === "DISPUTED",
          )
          .map((item) => Number(item.dimension_key)) ?? [];
      return new Set(isV10ReviewTask ? ids : [...ids, ...rawDisagreedCompetencyIds]);
    },
    [activeTask, isV10ReviewTask, rawDisagreedCompetencyIds],
  );
  const editableCompetencyIds = useMemo(
    () => new Set([...disputedCompetencyIds, ...unlockedCompetencyIds]),
    [disputedCompetencyIds, unlockedCompetencyIds],
  );
  const editableCompetencies = useMemo(
    () => visibleCompetencies.filter((item) => editableCompetencyIds.has(item.id)),
    [editableCompetencyIds, visibleCompetencies],
  );
  const lockedCompetencies = useMemo(
    () => visibleCompetencies.filter((item) => !editableCompetencyIds.has(item.id)),
    [editableCompetencyIds, visibleCompetencies],
  );
  const pendingReviewCount =
    poolSummary?.items.find((item) => item.status === "REVIEW_PENDING")?.count ?? 0;
  const aggregateLevels = useMemo(
    () =>
      new Map(activeTask?.aggregate.competencies.map((item) => [item.competency_id, item.level_value]) ?? []),
    [activeTask],
  );
  const lockedDisplayLevels = useMemo(() => {
    const levels = new Map(aggregateLevels);
    if (!isV10ReviewTask) return levels;
    activeTask?.consensus.dimensions
      .filter((item) => item.dimension_type === "competency" && item.consensus_status !== "DISPUTED")
      .forEach((item) => {
        levels.set(Number(item.dimension_key), item.recommended_level_value ?? 0);
      });
    return levels;
  }, [activeTask, aggregateLevels, isV10ReviewTask]);

  useEffect(() => {
    if (activeTask && activeTask.id !== activeTaskId) {
      setActiveTaskId(activeTask.id);
    }
  }, [activeTask, activeTaskId]);

  useEffect(() => {
    setUnlockedCompetencyIds([]);
  }, [activeTask?.id]);

  useEffect(() => {
    if (!activeTask) return;
    form.setFieldsValue({
      competencies: Object.fromEntries(
        visibleCompetencies.map((item) => [item.id, aggregateLevels.get(item.id) ?? 0]),
      ),
      review_comment: activeTask.review_comment ?? "",
    });
  }, [activeTask?.id, visibleCompetencies, aggregateLevels, form]);

  const unlockCompetency = (competencyId: number) => {
    setUnlockedCompetencyIds((current) =>
      current.includes(competencyId) ? current : [...current, competencyId],
    );
  };

  const handleUnlockLockedCompetency = (competencyId: number, competencyName: string) => {
    Modal.confirm({
      title: `解锁“${competencyName}”并修改？`,
      icon: <ExclamationCircleOutlined />,
      content:
        "该素养当前因标注意见一致而默认锁定。若你认为标注员存在遗漏或判断不当，可确认解锁后修改并提交复核结论。",
      okText: "确认解锁",
      cancelText: "取消",
      onOk: () => unlockCompetency(competencyId),
    });
  };

  const handleClaim = async () => {
    if (!reviewerId) {
      message.error("请先登录");
      return;
    }
    if (pendingReviewCount <= 0) {
      message.info("当前没有待复核题。");
      return;
    }
    const result = await claimMutation.mutateAsync({
      reviewer_user_id: reviewerId,
      count: pendingReviewCount,
    });
    message.success(`已领取 ${result.claimed_count} 道复核题`);
  };

  const handleAutoReconcile = async () => {
    if (!reviewerId) {
      message.error("请先登录");
      return;
    }
    const result = await reconcileMutation.mutateAsync({
      reviewer_user_id: reviewerId,
      include_unclaimed: true,
    });
    if (result.auto_closed_count > 0) {
      message.success(
        `已按当前规则自动关闭 ${result.auto_closed_count} 道可裁决复核题，仍需人工复核 ${result.still_disputed_count} 道。`,
      );
      setActiveTaskId(null);
      return;
    }
    message.info(
      result.scanned_count > 0
        ? `已检查 ${result.scanned_count} 道题，当前没有可自动关闭的旧复核任务。`
        : "当前没有可检查的待复核任务。",
    );
  };

  const handleSubmit = async (values: ReviewFormValues) => {
    if (!reviewerId || !activeTask) return;
    const competencyValues = values.competencies ?? {};
    const competencyPayload = editableCompetencies.map((item) => ({
      competency_id: item.id,
      level_value: competencyValues[item.id] ?? 0,
    }));
    await submitMutation.mutateAsync({
      reviewer_user_id: reviewerId,
      cognitive_level_id: null,
      competencies: competencyPayload,
      review_comment: values.review_comment ?? null,
    });
    message.success("复核已提交，题目进入已完成状态");
    form.resetFields();
    setActiveTaskId(null);
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={7}>
        <Card
          title="我的复核任务"
          extra={
            <Button
              icon={<InboxOutlined />}
              loading={claimMutation.isPending}
              onClick={handleClaim}
              disabled={pendingReviewCount <= 0}
            >
              一键领取全部复核题
            </Button>
          }
        >
          <Space style={{ marginBottom: 12 }}>
            <Button
              icon={<SyncOutlined />}
              loading={reconcileMutation.isPending}
              onClick={handleAutoReconcile}
            >
              按新规则清理可自动裁决题
            </Button>
          </Space>
          <Typography.Text type="secondary">
            当前{annotationStatusLabelMap.REVIEW_PENDING}池还有 {pendingReviewCount} 道题。当前仅有 1 位复核员，点击按钮会一次全部领取。
          </Typography.Text>
          {!isLoading && !taskData?.items.length ? (
            <Empty description="暂无已领取复核任务，可从待复核池一键领取" />
          ) : (
            <List
              loading={isLoading}
              dataSource={taskData?.items ?? []}
              renderItem={(item: ReviewTask) => (
                <List.Item
                  onClick={() => setActiveTaskId(item.id)}
                  style={{
                    cursor: "pointer",
                    background: item.id === activeTask?.id ? "#fff7e6" : undefined,
                    paddingInline: 8,
                    borderRadius: 6,
                  }}
                >
                  <List.Item.Meta
                    title={
                      <Space wrap>
                        <span>复核 #{item.id}</span>
                        <Tag color="red">题目 #{item.question_id}</Tag>
                      </Space>
                    }
                    description={item.question.content?.stem_text?.slice(0, 72) ?? "暂无题干"}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </Col>

      <Col xs={24} xl={17}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Card title="待复核题检查">
            {activeTask ? (
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                <Space wrap>
                  <Tag color="blue">题目 #{activeTask.question_id}</Tag>
                  <Tag>{activeTask.question.subject.name}</Tag>
                  {activeTask.question.grade ? <Tag>{activeTask.question.grade.grade_name}</Tag> : null}
                  <Tag color="red">一致率 {activeTask.aggregate.agreement_score ?? "-"}</Tag>
                  <Tag color={activeTask.consensus.consensus_status === "DISPUTED" ? "error" : "processing"}>
                    {getConsensusStatusLabel(activeTask.consensus.consensus_status)}
                  </Tag>
                </Space>
                <Typography.Text type="secondary">
                  当前共有 {activeTask.consensus.completed_annotation_count}/
                  {activeTask.consensus.required_annotations} 份标注，未解决分歧维度{" "}
                  {activeTask.consensus.unresolved_dimension_count} 个。
                </Typography.Text>
                <Alert
                  type="warning"
                  showIcon
                  message="复核员优先处理存在分歧的素养维度；已达成一致的素养默认锁定。若你认为标注意见存在遗漏，可点击已锁定素养，确认后解锁修改。"
                />
                <Button onClick={() => setDetailDrawerOpen(true)}>查看题目详情</Button>
                <QuestionRichText
                  html={activeTask.question.content?.stem_html}
                  text={activeTask.question.content?.stem_text}
                  emptyLabel="暂无题干"
                />
              </Space>
            ) : (
              <Empty description="请选择或领取一条待复核题" />
            )}
          </Card>

          {activeTask ? (
            <Card title="标注员提交结果">
              <Row gutter={[12, 12]}>
                {activeTask.annotations.map((annotation) => (
                  <Col xs={24} lg={8} key={annotation.annotation_id}>
                    <Card size="small" title={annotation.user_name} className="review-annotation-card">
                      <Space direction="vertical" size={8} style={{ width: "100%" }}>
                        {annotation.competencies.map((item) => (
                          <Tag
                            key={item.competency_id}
                            color={competencyLevelTagColor(item.level_value)}
                            className={item.level_value > 0 ? "review-annotation-tag--active" : undefined}
                          >
                            {item.competency_name}: L{item.level_value} · 信心等级
                            {confidenceLevelMeta(item.confidence_level ?? 5).label}
                          </Tag>
                        ))}
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          ) : null}

          {activeTask ? (
            <Card title="待复核素养投票分布">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                {activeTask.consensus.dimensions
                  .filter(
                    (item) =>
                      item.dimension_type === "competency" &&
                      item.consensus_status === "DISPUTED",
                  )
                  .map((dimension) => (
                    <div key={dimension.dimension_key}>
                      <Space wrap>
                        <Typography.Text strong>{dimension.dimension_label}</Typography.Text>
                        <Tag color="red">标注意见不一致</Tag>
                      </Space>
                      <Typography.Paragraph type="secondary" style={{ margin: "6px 0 0" }}>
                        {dimension.vote_summary
                          .map(
                            (vote) =>
                              `L${vote.level_value ?? "-"}：${vote.vote_count}票（${vote.annotator_names.join("、")}）`,
                          )
                          .join("；")}
                      </Typography.Paragraph>
                    </div>
                  ))}
              </Space>
            </Card>
          ) : null}

          {activeTask ? (
            <Card title="审核日志与操作历史">
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                {activeTask.review_logs.map((log) => (
                  <div key={log.id}>
                    <Space wrap>
                      <Tag color={log.actor_role === "admin" ? "red" : log.actor_role === "reviewer" ? "blue" : "default"}>
                        {log.actor_name ?? "系统"}
                      </Tag>
                      <Typography.Text strong>{log.action_label}</Typography.Text>
                      <Typography.Text type="secondary">{formatBackendDateTime(log.created_at)}</Typography.Text>
                    </Space>
                    {log.comment ? (
                      <Typography.Paragraph type="secondary" style={{ margin: "6px 0 0" }}>
                        {log.comment}
                      </Typography.Paragraph>
                    ) : null}
                  </div>
                ))}
              </Space>
            </Card>
          ) : null}

          <Card title="提交复核结论">
            {!activeTask ? (
              <Alert type="info" showIcon message="复核员领取待复核题后，可以检查已有标注结果并给出最终结论。" />
            ) : (
              <Form form={form} layout="vertical" onFinish={handleSubmit}>
                {lockedCompetencies.length ? (
                  <Card size="small" title="已自动锁定的一致素养" style={{ marginBottom: 16 }}>
                    <Space size={[8, 8]} wrap>
                      {lockedCompetencies.map((item) => {
                        const aggregateLevel = lockedDisplayLevels.get(item.id) ?? 0;
                        return (
                          <Button
                            key={item.id}
                            size="small"
                            icon={<LockOutlined />}
                            onClick={() => handleUnlockLockedCompetency(item.id, item.name)}
                          >
                            {item.name}: L{aggregateLevel}
                          </Button>
                        );
                      })}
                    </Space>
                    <Typography.Paragraph type="secondary" style={{ margin: "12px 0 0" }}>
                      点击任一锁定素养，可在确认“意见不一致需要修改”后将其解锁并加入下方可编辑区域。
                    </Typography.Paragraph>
                  </Card>
                ) : null}
                <Space direction="vertical" size={14} style={{ width: "100%" }}>
                  {editableCompetencies.map((item) => (
                    <div key={item.id} className="matrix-row">
                      <Space size={8}>
                        <Typography.Text strong>{item.name}</Typography.Text>
                        {disputedCompetencyIds.has(item.id) ? (
                          <Tag color="red">存在分歧</Tag>
                        ) : (
                          <Tag color="gold" icon={<UnlockOutlined />}>
                            已手动解锁
                          </Tag>
                        )}
                      </Space>
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

                <Form.Item name="review_comment" label="复核说明" style={{ marginTop: 16 }}>
                  <Input.TextArea rows={3} placeholder="可填写分歧原因、最终判断依据等" />
                </Form.Item>

                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SendOutlined />}
                  loading={submitMutation.isPending}
                >
                  提交复核
                </Button>
              </Form>
            )}
          </Card>
        </Space>
      </Col>
      <Drawer
        title={activeTask ? `题目 #${activeTask.question_id}` : "题目详情"}
        width={920}
        open={detailDrawerOpen}
        onClose={() => setDetailDrawerOpen(false)}
        destroyOnClose={false}
      >
        {questionDetailQuery.isLoading ? (
          <Result icon={<Spin size="large" />} title="正在加载题目详情" />
        ) : questionDetailQuery.data ? (
          <QuestionDetailSections detail={questionDetailQuery.data} />
        ) : (
          <Empty description="未找到题目详情" />
        )}
      </Drawer>
    </Row>
  );
}
