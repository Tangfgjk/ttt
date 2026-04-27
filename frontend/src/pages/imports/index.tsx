import type { ChangeEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

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
  useInitializeImportFolderUpload,
  useUploadImport,
  useUploadImportBatchChunk,
} from "@/modules/import-center/hooks";
import type { ImportBatch, ImportSourceRecord } from "@/types/imports";

type UploadListItem = {
  uid: string;
  name: string;
  originFileObj?: File;
};

type FileWithRelativePath = File & {
  webkitRelativePath?: string;
};

const DATA_SOURCE_OPTIONS = [
  { label: "dataset2_question_json", value: "dataset2_question_json" },
  { label: "dataset1_labeled", value: "dataset1_labeled" },
  { label: "dataset3_exam_sheet", value: "dataset3_exam_sheet" },
];

const FOLDER_UPLOAD_CHUNK_SIZE = 200;

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
    title: "文件标识",
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
    title: "归一化结果",
    dataIndex: "parse_status",
    width: 220,
    render: (value: string) => {
      const colorMap: Record<string, string> = {
        CREATED_NEW_QUESTION: "green",
        MATCHED_BY_EXTERNAL_ID: "blue",
        MATCHED_BY_CONTENT_HASH: "cyan",
        MATCHED_BY_REVIEW: "purple",
        CREATED_BY_REVIEW: "lime",
        PENDING_REVIEW: "gold",
        FAILED: "red",
        RAW_IMPORTED: "default",
      };
      return <Tag color={colorMap[value] ?? "default"}>{value}</Tag>;
    },
  },
  {
    title: "题目 ID",
    dataIndex: "normalized_question_id",
    width: 120,
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

function resolveAcceptedExtensions(dataSourceCode: string | undefined) {
  if (dataSourceCode === "dataset2_question_json") {
    return ".json";
  }
  return ".xlsx";
}

function chunkFiles(files: File[], chunkSize: number) {
  const chunks: File[][] = [];
  for (let index = 0; index < files.length; index += chunkSize) {
    chunks.push(files.slice(index, index + chunkSize));
  }
  return chunks;
}

export function ImportsPage() {
  const [form] = Form.useForm();
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const { data, isLoading } = useImportBatches();
  const uploadMutation = useUploadImport();
  const initializeFolderUploadMutation = useInitializeImportFolderUpload();
  const uploadBatchChunkMutation = useUploadImportBatchChunk();
  const [fileList, setFileList] = useState<UploadListItem[]>([]);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<number | undefined>(undefined);
  const [folderUploadProgress, setFolderUploadProgress] = useState<{
    currentChunk: number;
    totalChunks: number;
  } | null>(null);
  const dataSourceCode = Form.useWatch("data_source_code", form) as string | undefined;

  const batches = data ?? [];
  const detailQuery = useImportBatchDetail(selectedBatchId);
  const detail = detailQuery.data;

  useEffect(() => {
    if (!selectedBatchId && batches.length > 0) {
      setSelectedBatchId(batches[0].id);
    }
  }, [batches, selectedBatchId]);

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute("webkitdirectory", "");
      folderInputRef.current.setAttribute("directory", "");
    }
  }, []);

  const totalRecords = useMemo(
    () => batches.reduce((sum, item) => sum + item.total_records, 0),
    [batches],
  );
  const successBatches = useMemo(
    () => batches.filter((item) => item.import_status === "SUCCESS").length,
    [batches],
  );
  const folderName = useMemo(() => {
    const firstFile = folderFiles[0] as FileWithRelativePath | undefined;
    const relativePath = firstFile?.webkitRelativePath ?? "";
    return relativePath ? relativePath.split("/")[0] ?? "" : "";
  }, [folderFiles]);
  const isUploading =
    uploadMutation.isPending ||
    initializeFolderUploadMutation.isPending ||
    uploadBatchChunkMutation.isPending ||
    folderUploadProgress !== null;

  const handleFolderSelection = (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files ?? []);
    if (!selectedFiles.length) {
      setFolderFiles([]);
      return;
    }

    const accept = resolveAcceptedExtensions(dataSourceCode);
    const normalizedExtension = accept.replace(".", "").toLowerCase();
    const filteredFiles = selectedFiles.filter((file) =>
      file.name.toLowerCase().endsWith(`.${normalizedExtension}`),
    );

    setFolderFiles(filteredFiles);
    setFileList([]);

    if (!filteredFiles.length) {
      message.warning("当前文件夹里没有符合数据源要求的文件。");
      return;
    }

    message.success(`已选择文件夹，共识别 ${filteredFiles.length} 个可导入文件。`);
  };

  const handleUpload = async () => {
    const selectedDataSourceCode = form.getFieldValue("data_source_code") as string | undefined;
    const singleFile = fileList[0]?.originFileObj;

    if (!selectedDataSourceCode) {
      message.warning("请先选择数据源类型。");
      return;
    }

    try {
      if (folderFiles.length > 0) {
        const initBatch = await initializeFolderUploadMutation.mutateAsync({
          dataSourceCode: selectedDataSourceCode,
          folderName,
          fileCount: folderFiles.length,
        });
        setSelectedBatchId(initBatch.id);

        const chunks = chunkFiles(folderFiles, FOLDER_UPLOAD_CHUNK_SIZE);
        let totalImportedRecords = 0;

        for (const [index, chunk] of chunks.entries()) {
          setFolderUploadProgress({
            currentChunk: index + 1,
            totalChunks: chunks.length,
          });
          const result = await uploadBatchChunkMutation.mutateAsync({
            batchId: initBatch.id,
            files: chunk,
            finalize: index === chunks.length - 1,
          });
          totalImportedRecords += result.imported_records;
          setSelectedBatchId(result.batch.id);
        }

        setFolderUploadProgress(null);
        setFolderFiles([]);
        if (folderInputRef.current) {
          folderInputRef.current.value = "";
        }
        message.success(`文件夹导入完成，共处理 ${totalImportedRecords} 条记录。`);
        return;
      }

      if (!singleFile) {
        message.warning("请先选择要上传的文件，或者选择一个文件夹。");
        return;
      }

      const result = await uploadMutation.mutateAsync({
        dataSourceCode: selectedDataSourceCode,
        file: singleFile,
      });
      message.success(`导入完成，共处理 ${result.imported_records} 条记录。`);
      setSelectedBatchId(result.batch.id);
      setFileList([]);
      form.resetFields(["file"]);
    } catch (error) {
      setFolderUploadProgress(null);
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
          当前支持单文件上传，也支持把一个文件夹中的多个数据文件分片上传并合并为同一个批次。
          对于大量 dataset2 JSON 文件的场景，建议使用文件夹批量上传。
        </Typography.Paragraph>
      </Card>

      <Card>
        <Form form={form} layout="vertical" initialValues={{ data_source_code: "dataset2_question_json" }}>
          <Row gutter={[16, 16]} align="bottom">
            <Col xs={24} md={8}>
              <Form.Item label="数据源类型" name="data_source_code">
                <Select
                  options={DATA_SOURCE_OPTIONS}
                  onChange={() => {
                    setFileList([]);
                    setFolderFiles([]);
                    setFolderUploadProgress(null);
                    if (folderInputRef.current) {
                      folderInputRef.current.value = "";
                    }
                  }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="单文件上传" name="file">
                <Upload
                  beforeUpload={() => false}
                  maxCount={1}
                  fileList={fileList}
                  accept={resolveAcceptedExtensions(dataSourceCode)}
                  onChange={({ fileList: nextFileList }: { fileList: UploadListItem[] }) => {
                    setFileList(nextFileList);
                    if (nextFileList.length > 0) {
                      setFolderFiles([]);
                      setFolderUploadProgress(null);
                      if (folderInputRef.current) {
                        folderInputRef.current.value = "";
                      }
                    }
                  }}
                >
                  <Button>选择文件</Button>
                </Upload>
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label="文件夹批量上传">
                <Space direction="vertical" size={8} style={{ width: "100%" }}>
                  <Button block onClick={() => folderInputRef.current?.click()}>
                    选择文件夹
                  </Button>
                  <Typography.Text type="secondary">
                    {folderFiles.length > 0
                      ? `已选择 ${folderFiles.length} 个文件${folderName ? `，目录：${folderName}` : ""}`
                      : "适合批量导入一个目录下的大量 JSON / Excel 文件。"}
                  </Typography.Text>
                  {folderUploadProgress ? (
                    <Typography.Text type="secondary">
                      正在分片上传：第 {folderUploadProgress.currentChunk} / {folderUploadProgress.totalChunks} 批
                    </Typography.Text>
                  ) : null}
                  <input
                    ref={folderInputRef}
                    type="file"
                    multiple
                    accept={resolveAcceptedExtensions(dataSourceCode)}
                    style={{ display: "none" }}
                    onChange={handleFolderSelection}
                  />
                </Space>
              </Form.Item>
            </Col>
            <Col xs={24}>
              <Button type="primary" loading={isUploading} onClick={() => void handleUpload()}>
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
                当前选中批次来自 {detail.batch.data_source_code}，文件标识为 {detail.batch.file_name}。
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
