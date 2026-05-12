import {
  CheckCircleOutlined,
  DatabaseOutlined,
  ForkOutlined,
  RadarChartOutlined,
} from "@ant-design/icons";
import { Card, Col, List, Progress, Row, Space, Statistic, Tag, Typography } from "antd";

const completedTimeline = [
  {
    stage: "V1",
    title: "项目底座与账号体系",
    description: "完成基础登录、角色划分、数据库底座和后端服务骨架。",
  },
  {
    stage: "V2",
    title: "导入链路与统一题池",
    description:
      "三类数据导入接通，统一题池支持筛选、分页、详情抽屉与来源映射查看。",
  },
  {
    stage: "V3",
    title: "判重与人工复核",
    description:
      "自动判重、疑似重复人工复核、管理员按相似度批量确认重复等治理能力落地。",
  },
  {
    stage: "V4.5",
    title: "嵌入可视化与题池联动",
    description:
      "试题嵌入补全、二维分布可视化、缓存优化与跳转统一题池联动已经接通。",
  },
  {
    stage: "V4.7",
    title: "主动学习训练闭环",
    description:
      "训练、模型版本、低置信度预测选题、CoreSet 选题、GPU worker 与可复现训练打通。",
  },
  {
    stage: "V4.8",
    title: "训练监控与治理能力",
    description:
      "训练监控页、趋势分组、模型版本治理、预测取消与真实 batch 级进度补齐。",
  },
  {
    stage: "V4.10",
    title: "题池回收与批次撤回",
    description:
      "系统管理员可查看各题池、统一回收待标注/领取中题目，并撤回某次 CoreSet 或低置信度选题批次。",
  },
];

const nextItems = [
  "继续完善标注闭环与推荐闭环的真实联调，观察新增标注数据带来的模型趋势变化。",
  "补强训练、预测、导入与复核任务的审计、取消、恢复与失败重试能力。",
  "优化大规模候选池下的 CoreSet 与低置信度选题性能，补充分层筛选与批处理策略。",
  "整理上线前的权限、安全、运维与正式评估流程，形成稳定可部署版本。",
];

export function HomePage() {
  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card className="hero-panel">
        <Typography.Title level={2} style={{ marginTop: 0 }}>
          项目总览
        </Typography.Title>
        <Typography.Paragraph>
          当前项目已经从早期“设计与底座搭建”推进到“主动学习训练闭环联调与治理优化”阶段。
          统一题池、导入、判重、人工复核、试题嵌入可视化、训练监控和模型驱动选题已经形成一条可运行主链路，
          V4 阶段已经基本收束，下一步将进入 V5，重点推进正式评估、性能优化与上线前治理。
        </Typography.Paragraph>
        <Progress percent={92} strokeColor="#0f766e" />
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="当前阶段"
              value="V4.10 治理收束"
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="核心方向"
              value="统一题池 + 主动学习 + 标注闭环"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="下一关键动作"
              value="稳定联调与正式评估"
              prefix={<ForkOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card>
            <Statistic title="整体进度" value={92} suffix="%" prefix={<RadarChartOutlined />} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <Statistic title="已完成阶段" value={7} suffix="个" />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card>
            <Statistic title="当前主攻方向" value="治理优化 + 闭环稳定性" />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="已完成内容">
            <div className="project-timeline">
              {completedTimeline.map((item) => (
                <div key={item.stage} className="project-timeline__item">
                  <div className="project-timeline__rail" />
                  <div className="project-timeline__content">
                    <Space size={10} wrap>
                      <Tag color="green">完成</Tag>
                      <Tag color="blue">{item.stage}</Tag>
                      <Typography.Text strong>{item.title}</Typography.Text>
                    </Space>
                    <Typography.Paragraph type="secondary" style={{ margin: "8px 0 0" }}>
                      {item.description}
                    </Typography.Paragraph>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="下一步待办">
            <List
              dataSource={nextItems}
              renderItem={(item: string) => (
                <List.Item>
                  <Space align="start">
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
