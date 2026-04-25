import { Card, Col, Row, Space, Typography } from "antd";

const adminPanels = [
  {
    title: "用户与角色",
    desc: "后续接入真实用户、权限、培训准入与角色管理。",
  },
  {
    title: "导入与批次",
    desc: "观察导入批次、失败记录、归一化进度和异常处理。",
  },
  {
    title: "判重复核",
    desc: "后续这里会接入 question_duplicate_candidates 的人工复核入口。",
  },
  {
    title: "题目治理",
    desc: "统一题池中的题目校验、合并确认、映射维护等管理能力。",
  },
];

export function AdminPage() {
  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          管理后台
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          第一阶段会优先把导入监控、题目治理和判重复核做出来，方便你直接观察统一题池构建过程。
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        {adminPanels.map((panel) => (
          <Col xs={24} md={12} key={panel.title}>
            <Card title={panel.title}>
              <Typography.Paragraph style={{ marginBottom: 0 }}>
                {panel.desc}
              </Typography.Paragraph>
            </Card>
          </Col>
        ))}
      </Row>
    </Space>
  );
}
