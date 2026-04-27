import { useEffect, useMemo, useState } from "react";

import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";

import {
  useImportBatchDetail,
  useImportBatches,
  useUploadImport,
} from "@/modules/import-center/hooks";
import type { ImportBatch, ImportSourceRecord } from "@/types/imports";

type UploadListItem = {
  uid: string;
  name: string;
  originFileObj?: File;
};

const DATA_SOURCE_OPTIONS = [
  { label: "dataset2_question_json", value: "dataset2_question_json" },
  { label: "dataset1_labeled", value: "dataset1_labeled" },
  { label: "dataset3_exam_sheet", value: "dataset3_exam_sheet" },
];

const batchColumns = [
  {
    title: "批次号",
    dataIndex: "batch_no",
    width: 220,
  },
  {
    title: "数据源",
    dataIndex: "data_source_code",
    width: 180,
    render: (_: unknown, record: ImportBatch) => (
      <Space direction="vertical" size={0}>
        <Typography.Text>{record.data_source_code}</Typography.Text>
        <Typography.Text type="secondary">{record.data_source_name}</Typography.Text>
      </Space>
    ),
  },
  {
    title: "文件名",
    dataIndex: "file_name",
  },
  {
    title: "状态",
    dataIndex: "import_status",
    width: 160,
    render: (value: string) => {
      const color =
        value === "SUCCESS" ? "green" : value === "FAILED" ? "red" : value === "PARTIAL_SUCCESS" ? "gold" : "blue";
      return <Tag color={color}>{value}</Tag>;
    },
  },
  {
    title: "总记录",
    dataIndex: "total_records",
    width: 100,
  },
  {
    title: "成功",
    dataIndex: "success_records",
    width: 100,
  },
  {
    title: "失败",
    dataIndex: "failed_records",
    width: 100,
  },
];

const recordColumns = [
  {
    title: "源记录键",
    dataIndex: "source_record_key",
    width: 220,
  },
  {
    title: "判重/归一化结果",
    dataIndex: "parse_status",
    width: 220,
    render: (value: string) => {
      const colorMap: Record<string, string> = {
        CREATED_NEW_QUESTION: "green",
        MATCHED_BY_EXTERNAL_ID: "blue",
        MATCHED_BY_CONTENT_HASH: "cyan",
        PENDING_REVIEW: "gold",
        FAILED: "red",
        RAW_IMPORTED: "default",
      };
      return <Tag color={colorMap[value] ?? "default"}>{value}</Tag>;
    },
  },
  {
    title: "题目ID",
    dataIndex: "normalized_question_id",
    width: 100,
    render: (value?: number | null) => value ?? "-",
  },
  {
    title: "候选重复数",
    dataIndex: "duplicate_candidate_count",
    width: 120,
  },
  {
    title: "内容指纹",
    dataIndex: "normalized_hash",
    ellipsis: true,
    render: (value?: string | null) => value ?? "-",
  },
  {
    title: "错误信息",
    dataIndex: "error_message",
    ellipsis: true,
    render: (value?: string | null) => value ?? "-",
  },
];

export function ImportsPage() {
  const [form] = Form.useForm();
  const { data, isLoading } = useImportBatches();
  const uploadMutation = useUploadImport();
  const [fileList, setFileList] = useState<UploadListItem[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<number | undefined>(undefined);

  const batches = data ?? [];
  const detailQuery = useImportBatchDetail(selectedBatchId);
  const detail = detailQuery.data;

  useEffect(() => {
    if (!selectedBatchId && batches.length > 0) {
      setSelectedBatchId(batches[0].id);
    }
  }, [batches, selectedBatchId]);

  const totalRecords = useMemo(
    () => batches.reduce((sum, item) => sum + item.total_records, 0),
    [batches],
  );
  const successBatches = useMemo(
    () => batches.filter((item) => item.import_status === "SUCCESS").length,
    [batches],
  );

  const handleUpload = async () => {
    const dataSourceCode = form.getFieldValue("data_source_code");
    const file = fileList[0]?.originFileObj;
    if (!dataSourceCode) {
      message.warning("请先选择数据源类型。");
      return;
    }
    if (!file) {
      message.warning("请先选择要上传的文件。");
      return;
    }

    try {
      const result = await uploadMutation.mutateAsync({
        dataSourceCode,
        file,
      });
      message.success(`导入完成，共处理 ${result.imported_records} 条记录。`);
      setSelectedBatchId(result.batch.id);
      setFileList([]);
      form.resetFields(["file"]);
    } catch (error) {
      const detailMessage =
        error instanceof Error ? error.message : "上传失败，请查看后端日志。";
      message.error(detailMessage);
    }
  };

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      <Card>
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          导入中心
        </Typography.Title>
        <Typography.Paragraph type="secondary">
          这一版已经支持单文件上传导入，并且会在 dataset2 的归一化阶段接入题目判重。导入完成后，你可以直接在下方看到批次结果、新建题目数量、判重命中数量和待人工复核记录。
        </Typography.Paragraph>
      </Card>

      <Card>
        <Form form={form} layout="vertical" initialValues={{ data_source_code: "dataset2_question_json" }}>
          <Row gutter={[16, 16]} align="bottom">
            <Col xs={24} md={8}>
              <Form.Item label="数据源类型" name="data_source_code">
                <Select options={DATA_SOURCE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} md={10}>
              <Form.Item label="上传文件" name="file">
                <Upload
                  beforeUpload={() => false}
                  maxCount={1}
                  fileList={fileList}
                  onChange={({ fileList: nextFileList }: { fileList: UploadListItem[] }) =>
                    setFileList(nextFileList)
                  }
                >
                  <Button>选择文件</Button>
                </Upload>
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Button
                type="primary"
                block
                loading={uploadMutation.isPending}
                onClick={() => void handleUpload()}
              >
                开始导入
              </Button>
            </Col>
          </Row>
        </Form>
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
          <Empty description="当前还没有导入批次。" />
        ) : (
          <Table<ImportBatch>
            rowKey="id"
            loading={isLoading}
            columns={batchColumns}
            dataSource={batches}
            pagination={false}
            scroll={{ x: 1080 }}
            onRow={(record: ImportBatch) => ({
              // Keeping the batch table clickable makes it easy to switch
              // between import runs while we are still building the full
              // management workflow around import batches.
              onClick: () => setSelectedBatchId(record.id),
            })}
            rowClassName={(record: ImportBatch) =>
              record.id === selectedBatchId ? "ant-table-row-selected" : ""
            }
          />
        )}
      </Card>

      <Card loading={detailQuery.isLoading}>
        {!detail ? (
          <Empty description="请选择一个批次查看详情。" />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <div>
              <Typography.Title level={4} style={{ marginTop: 0 }}>
                批次详情：{detail.batch.batch_no}
              </Typography.Title>
              <Typography.Paragraph type="secondary">
                当前选中批次来自 {detail.batch.data_source_code}，文件为 {detail.batch.file_name}。
              </Typography.Paragraph>
            </div>

            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="新建题目" value={detail.summary.created_new_question} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="外部 ID 命中" value={detail.summary.matched_by_external_id} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="内容指纹命中" value={detail.summary.matched_by_content_hash} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="待人工复核" value={detail.summary.pending_review} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="失败记录" value={detail.summary.failed} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="总记录" value={detail.summary.total_records} />
                </Card>
              </Col>
            </Row>

            <Table<ImportSourceRecord>
              rowKey="id"
              columns={recordColumns}
              dataSource={detail.records}
              pagination={false}
              scroll={{ x: 1400 }}
            />
          </Space>
        )}
      </Card>
    </Space>
  );
}
