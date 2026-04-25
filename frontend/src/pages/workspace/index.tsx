import { Card, Col, List, Row, Space, Statistic, Tag, Typography } from "antd";

import { useAuthStore } from "@/app/store/auth-store";

const myTodoItems = [
  "继续处理推荐题目池中的待标注题",
  "完成至少一轮核心素养矩阵标注",
  "关注争议题和复核反馈",
];

export function WorkspacePage() {
  const session = useAuthStore((state) => state.session);

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card className="hero-panel">
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          我的工作台
        </Typography.Title>
        <Typography.Paragraph>
          这是用户端首页，主要服务于标注员和复核员。这里会优先展示“我今天该做什么”，而不是管理侧的项目全局进度。
        </Typography.Paragraph>
        <Tag color="green">{session?.name}</Tag>
        <Tag color="blue">{session?.role === "reviewer" ? "复核视角" : "标注视角"}</Tag>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="我的待办题目" value={12} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="今日已完成" value={4} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="争议待复核" value={session?.role === "reviewer" ? 3 : 0} />
          </Card>
        </Col>
      </Row>

      <Card title="当前建议动作">
        <List
          dataSource={myTodoItems}
          renderItem={(item: string) => (
            <List.Item>
              <Space>
                <Tag color="gold">待做</Tag>
                <span>{item}</span>
              </Space>
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}
