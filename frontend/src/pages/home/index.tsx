import { CheckCircleOutlined, DatabaseOutlined, ForkOutlined } from "@ant-design/icons";
import { Card, Col, List, Progress, Row, Space, Statistic, Tag, Typography } from "antd";

const completedItems = [
  "MySQL 表结构与 Alembic 基线已落地",
  "原始导入底座已支持 3 类样例格式",
  "统一题池与题目判重规则已定稿",
  "判重服务与支撑表已实际落库",
];

const nextItems = [
  "把 QuestionDedupService 正式接进归一化导入流水线",
  "打通 dataset2 到 questions / question_contents / question_external_refs",
  "建设题库页与导入批次页的真实联调",
  "开始标注工作台的提交闭环",
];

export function HomePage() {
  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card className="hero-panel">
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          项目总览
        </Typography.Title>
        <Typography.Paragraph>
          当前项目已经从纯设计阶段进入“可运行底座”阶段。后续最关键的是把判重和统一题池正式接进归一化导入流水线，这会直接决定后续题库、标注和推荐是否稳定。
        </Typography.Paragraph>
        <Progress percent={42} strokeColor="#0f766e" />
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="当前阶段" value="底座完成" prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="核心方向" value="统一题池" prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="下一关键动作" value="归一化导入" prefix={<ForkOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="已完成内容">
            <List
              dataSource={completedItems}
              renderItem={(item: string) => (
                <List.Item>
                  <Space>
                    <Tag color="green">完成</Tag>
                    <span>{item}</span>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="下一步待办">
            <List
              dataSource={nextItems}
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
        </Col>
      </Row>
    </Space>
  );
}
