import { Button, Card, Col, Empty, Row, Space, Spin, Statistic, Tag, Typography, message } from "antd";

import { useAuthStore } from "@/app/store/auth-store";
import {
  useApproveDuplicateCandidate,
  useDuplicateReviewCandidates,
  useRejectDuplicateCandidate,
} from "@/modules/dedup-review/hooks";

function toScore(value: string | number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function DedupReviewPage() {
  const session = useAuthStore((state) => state.session);
  const { data, isLoading } = useDuplicateReviewCandidates();
  const approveMutation = useApproveDuplicateCandidate();
  const rejectMutation = useRejectDuplicateCandidate();

  const candidates = data ?? [];
  const pendingCount = candidates.filter((item) => item.review_status === "PENDING").length;
  const highConfidenceCount = candidates.filter((item) => toScore(item.confidence_score) >= 0.99).length;

  const handleApprove = async (candidateId: number) => {
    if (!session) {
      return;
    }
    try {
      const result = await approveMutation.mutateAsync({
        candidateId,
        reviewedByUserId: session.id,
      });
      message.success(`已确认重复，题目挂接到 #${result.normalized_question_id}。`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "审核失败。");
    }
  };

  const handleReject = async (candidateId: number) => {
    if (!session) {
      return;
    }
    try {
      const result = await rejectMutation.mutateAsync({
        candidateId,
        reviewedByUserId: session.id,
      });
      message.success(`已确认不重复，并新建题目 #${result.normalized_question_id}。`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : "审核失败。");
    }
  };

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          疑似重复人工复核
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          这里展示系统自动判重后仍拿不准的候选对。`reviewer` 负责确认是否与已有题合并，`admin` 可以进入查看并做兜底监督。
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="待复核候选" value={pendingCount} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="高置信候选" value={highConfidenceCount} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="当前审核人" value={session?.name ?? "-"} />
          </Card>
        </Col>
      </Row>

      {isLoading ? (
        <Card>
          <Spin />
        </Card>
      ) : !candidates.length ? (
        <Card>
          <Empty description="当前没有待复核的疑似重复题。" />
        </Card>
      ) : (
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          {candidates.map((item) => (
            <Card key={item.candidate_id}>
              <Space direction="vertical" size={16} style={{ width: "100%" }}>
                <Space wrap>
                  <Tag color="gold">{item.review_status}</Tag>
                  <Tag color="blue">{item.match_type}</Tag>
                  <Tag color="cyan">相似度 {toScore(item.confidence_score).toFixed(4)}</Tag>
                  <Tag>批次 {item.source_record.batch_no}</Tag>
                  <Tag>{item.source_record.data_source_code}</Tag>
                </Space>

                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card size="small" title={`新导入记录 #${item.source_record.source_record_id}`}>
                      <Typography.Paragraph>
                        <strong>题干：</strong>
                        {item.source_record.source_stem_text}
                      </Typography.Paragraph>
                      <Typography.Paragraph>
                        <strong>答案：</strong>
                        {item.source_record.source_answer_text ?? "-"}
                      </Typography.Paragraph>
                      <Typography.Text type="secondary">
                        源记录键：{item.source_record.source_record_key}
                      </Typography.Text>
                    </Card>
                  </Col>

                  <Col xs={24} lg={12}>
                    <Card size="small" title={`候选旧题 #${item.candidate_question.question_id}`}>
                      <Typography.Paragraph>
                        <strong>题干：</strong>
                        {item.candidate_question.stem_text}
                      </Typography.Paragraph>
                      <Typography.Paragraph>
                        <strong>答案：</strong>
                        {item.candidate_question.answer_text ?? "-"}
                      </Typography.Paragraph>
                      <Typography.Text type="secondary">
                        现有题目 ID：{item.candidate_question.question_id}
                      </Typography.Text>
                    </Card>
                  </Col>
                </Row>

                <Space wrap>
                  <Tag>stem_similarity: {String(item.comparison_snapshot.stem_similarity ?? "-")}</Tag>
                  <Tag>answer_exact: {String(item.comparison_snapshot.answer_exact ?? "-")}</Tag>
                  <Tag>grade_distance: {String(item.comparison_snapshot.grade_distance ?? "-")}</Tag>
                  <Tag>
                    content_hash_equal: {String(item.comparison_snapshot.content_hash_equal ?? "-")}
                  </Tag>
                </Space>

                <Space>
                  <Button
                    type="primary"
                    loading={approveMutation.isPending}
                    onClick={() => void handleApprove(item.candidate_id)}
                  >
                    确认重复
                  </Button>
                  <Button
                    danger
                    loading={rejectMutation.isPending}
                    onClick={() => void handleReject(item.candidate_id)}
                  >
                    确认不重复
                  </Button>
                </Space>
              </Space>
            </Card>
          ))}
        </Space>
      )}
    </Space>
  );
}
