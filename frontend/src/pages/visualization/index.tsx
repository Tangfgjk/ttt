import { Card, Col, Empty, Row, Space, Statistic, Typography } from "antd";

export function VisualizationPage() {
  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          可视化
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          第二阶段会在这里接题目嵌入降维、推荐批次高亮、主动学习曲线等图表。
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="计划图表" value="2D 散点图" />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="主要数据源" value="question_embeddings" />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="当前状态" value="待接后端数据" />
          </Card>
        </Col>
      </Row>

      <Card>
        <Empty description="可视化图表将在第二阶段接入 ECharts 与投影数据接口" />
      </Card>
    </Space>
  );
}
