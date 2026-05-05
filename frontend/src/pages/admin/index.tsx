import { CheckCircleOutlined, DatabaseOutlined, ThunderboltOutlined } from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  InputNumber,
  Row,
  Select,
  Space,
  Statistic,
  Typography,
  message,
} from "antd";

import {
  useAnnotationPoolSummary,
  useSelectionStrategies,
  useSelectQuestionsForAnnotation,
} from "@/modules/annotations/hooks";
import { useAuthStore } from "@/app/store/auth-store";
import type { SelectionStrategy } from "@/types/annotations";

const statusLabels: Record<string, string> = {
  PENDING: "未标注池",
  WAITING: "待标注池",
  IN_PROGRESS: "领取封锁中",
  REVIEW_PENDING: "待复核池",
  COMPLETED: "已完成",
};

export function AdminPage() {
  const [form] = Form.useForm();
  const session = useAuthStore((state) => state.session);
  const { data: summary, isLoading: isSummaryLoading } = useAnnotationPoolSummary();
  const { data: strategies, isLoading: isStrategiesLoading } = useSelectionStrategies();
  const selectMutation = useSelectQuestionsForAnnotation();

  const handleSelect = async (values: { strategy: SelectionStrategy; count: number }) => {
    const result = await selectMutation.mutateAsync({
      strategy: values.strategy,
      count: values.count,
      triggered_by_user_id: session?.id ?? null,
    });
    message.success(`已将 ${result.moved_count} 道题加入待标注池`);
  };

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          管理后台
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          管理员可以从未标注池中按 CoreSet 策略挑选题目，形成待标注池，再由标注员领取。
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        {(summary?.items ?? []).map((item) => (
          <Col xs={24} sm={12} lg={8} xl={4} key={item.status}>
            <Card>
              <Statistic
                loading={isSummaryLoading}
                title={statusLabels[item.status] ?? item.status}
                value={item.count}
                prefix={item.status === "COMPLETED" ? <CheckCircleOutlined /> : <DatabaseOutlined />}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Card
        title="CoreSet 抽题"
        extra={
          <Space>
            <ThunderboltOutlined />
            <span>未标注池到待标注池</span>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="每次至少挑选 100 道题。Facility Location、Graph Cut 和 MoE 会先在候选池中做轻量筛选，避免大池子计算过慢。"
        />
        <Form
          form={form}
          layout="inline"
          initialValues={{ strategy: "moe", count: 100 }}
          onFinish={handleSelect}
        >
          <Form.Item
            label="策略"
            name="strategy"
            rules={[{ required: true, message: "请选择策略" }]}
          >
            <Select
              loading={isStrategiesLoading}
              style={{ width: 260 }}
              options={(strategies ?? []).map((item) => ({
                value: item.code,
                label: `${item.name} (${item.code})`,
              }))}
            />
          </Form.Item>
          <Form.Item
            label="数量"
            name="count"
            rules={[{ required: true, message: "请输入挑选数量" }]}
          >
            <InputNumber min={100} max={1000} step={10} style={{ width: 140 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={selectMutation.isPending}>
              挑选并加入待标注池
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
}
