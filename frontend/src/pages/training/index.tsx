import { Card, Empty, Space, Table, Tag, Typography } from "antd";

const demoRows = [
  { id: "T-1024", status: "PENDING", algorithm: "Herding", samples: 1200 },
  { id: "T-1023", status: "SUCCESS", algorithm: "K-Means", samples: 900 },
];

export function TrainingPage() {
  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          训练监控
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          当前先展示训练页骨架，后续接 `training_tasks`、模型指标和主动学习效果曲线。
        </Typography.Paragraph>
      </Card>

      <Card>
        {!demoRows.length ? (
          <Empty description="当前没有训练任务" />
        ) : (
          <Table
            rowKey="id"
            pagination={false}
            dataSource={demoRows}
            columns={[
              { title: "任务 ID", dataIndex: "id" },
              {
                title: "状态",
                dataIndex: "status",
                render: (value: string) => (
                  <Tag color={value === "SUCCESS" ? "green" : "gold"}>{value}</Tag>
                ),
              },
              { title: "算法", dataIndex: "algorithm" },
              { title: "样本数", dataIndex: "samples" },
            ]}
          />
        )}
      </Card>
    </Space>
  );
}
