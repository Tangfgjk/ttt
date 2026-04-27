import { CheckCircleOutlined, DatabaseOutlined, ForkOutlined } from "@ant-design/icons";
import { Card, Col, List, Progress, Row, Space, Statistic, Tag, Typography } from "antd";

const completedItems = [
  "MySQL 表结构、Alembic 迁移和后端底座已稳定落地",
  "三类数据导入已接通，支持单文件与文件夹批量导入",
  "统一题池与题目判重规则已落地，自动判重与人工复核可用",
  "统一题池页面已支持筛选、分页、详情抽屉与原始文本对照",
];

const nextItems = [
  "打通标注工作台从领取、保存草稿到提交的完整闭环",
  "将大批量导入升级为更稳的异步批处理，并补齐失败重试",
  "为复核结果补充审计日志与错误合并回滚能力",
  "推进推荐、训练与可视化模块进入真实联调阶段",
];

export function HomePage() {
  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card className="hero-panel">
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          项目总览
        </Typography.Title>
        <Typography.Paragraph>
          当前项目已经从“设计与底座阶段”进入“可运行联调阶段”。统一题池、导入、判重、人工复核和题库浏览主链路已经成立，接下来最关键的是把标注闭环、异步导入与训练推荐模块继续做深做稳。
        </Typography.Paragraph>
        <Progress percent={72} strokeColor="#0f766e" />
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="当前阶段" value="V3 可运行联调" prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="核心方向" value="统一题池 + 标注闭环" prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="下一关键动作" value="标注闭环与异步导入" prefix={<ForkOutlined />} />
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
