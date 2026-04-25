import { Card, Col, Empty, Row, Space, Statistic, Table, Tag, Typography } from "antd";

import { useImportBatches } from "@/modules/import-center/hooks";
import type { ImportBatch } from "@/types/imports";

const columns = [
  {
    title: "批次号",
    dataIndex: "batch_no",
    width: 220,
  },
  {
    title: "文件名",
    dataIndex: "file_name",
  },
  {
    title: "状态",
    dataIndex: "import_status",
    width: 140,
    render: (value: string) => {
      const color = value === "SUCCESS" ? "green" : value === "FAILED" ? "red" : "gold";
      return <Tag color={color}>{value}</Tag>;
    },
  },
  {
    title: "总记录",
    dataIndex: "total_records",
    width: 110,
  },
  {
    title: "成功",
    dataIndex: "success_records",
    width: 110,
  },
  {
    title: "失败",
    dataIndex: "failed_records",
    width: 110,
  },
];

export function ImportsPage() {
  const { data, isLoading } = useImportBatches();
  const batches = data ?? [];

  const totalRecords = batches.reduce((sum, item) => sum + item.total_records, 0);
  const successBatches = batches.filter((item) => item.import_status === "SUCCESS").length;

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          导入中心
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          当前页面优先承担“观察导入进度”的职责。等归一化流水线接上以后，这里还会继续展示统一题池入库情况、判重命中情况和疑似重复候选。
        </Typography.Paragraph>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="导入批次数" value={batches.length} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="成功批次" value={successBatches} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="累计原始记录" value={totalRecords} />
          </Card>
        </Col>
      </Row>

      <Card>
        {!isLoading && !batches.length ? (
          <Empty description="当前还没有导入批次" />
        ) : (
          <Table<ImportBatch>
            rowKey="id"
            loading={isLoading}
            columns={columns}
            dataSource={batches}
            pagination={false}
            scroll={{ x: 960 }}
          />
        )}
      </Card>
    </Space>
  );
}
