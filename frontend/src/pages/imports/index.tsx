import type { ChangeEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Progress,
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
import { useNavigate } from "react-router-dom";

import {
  useImportBatchDetail,
  useImportBatches,
  useInitializeImportFolderUpload,
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

type JsonChunkFile = {
  file: File;
  recordCount: number;
};

type ImportProgressState = {
  mode: "folder" | "large-json" | "single-file";
  phase: "preparing" | "uploading";
  currentChunk: number;
  totalChunks: number;
  processedRecords: number;
  totalRecords?: number;
  fileName: string;
};

const DATA_SOURCE_OPTIONS = [
  { label: "dataset2_question_json", value: "dataset2_question_json" },
  { label: "dataset1_labeled", value: "dataset1_labeled" },
  { label: "dataset3_exam_sheet", value: "dataset3_exam_sheet" },
];

const FOLDER_UPLOAD_CHUNK_SIZE = 500;
const LARGE_JSON_FILE_THRESHOLD_BYTES = 10 * 1024 * 1024;
const LARGE_JSON_RECORD_CHUNK_SIZE = 1000;
const LARGE_JSON_UPLOAD_REQUEST_CHUNK_SIZE = 5;

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

function chunkItems<T>(items: T[], chunkSize: number) {
  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += chunkSize) {
    chunks.push(items.slice(index, index + chunkSize));
  }
  return chunks;
}

function isActiveImportStatus(status: string | undefined) {
  return status === "UPLOADING" || status === "QUEUED" || status === "RUNNING";
}

function formatDuration(seconds: number) {
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "不到 1 分钟";
  }
  const roundedSeconds = Math.round(seconds);
  const hours = Math.floor(roundedSeconds / 3600);
  const minutes = Math.floor((roundedSeconds % 3600) / 60);
  const remainSeconds = roundedSeconds % 60;

  if (hours > 0) {
    return `${hours} 小时 ${minutes} 分钟`;
  }
  if (minutes > 0) {
    return `${minutes} 分钟 ${remainSeconds} 秒`;
  }
  return `${remainSeconds} 秒`;
}

function shouldUseChunkedJsonUpload(dataSourceCode: string | undefined, file: File | undefined) {
  return (
    dataSourceCode === "dataset2_question_json" &&
    typeof file !== "undefined" &&
    file.size >= LARGE_JSON_FILE_THRESHOLD_BYTES
  );
}

function createChunkFileName(originalName: string, partIndex: number) {
  const extensionIndex = originalName.lastIndexOf(".");
  const hasExtension = extensionIndex > 0;
  const baseName = hasExtension ? originalName.slice(0, extensionIndex) : originalName;
  const extension = hasExtension ? originalName.slice(extensionIndex) : ".json";
  return `${baseName}.part-${String(partIndex).padStart(4, "0")}${extension}`;
}

async function splitJsonFileIntoChunks(file: File, recordsPerChunk: number) {
  const rawText = await file.text();
  const payload = JSON.parse(rawText) as unknown;

  if (Array.isArray(payload)) {
    const files: JsonChunkFile[] = [];
    for (let index = 0; index < payload.length; index += recordsPerChunk) {
      const chunkItems = payload.slice(index, index + recordsPerChunk);
      files.push({
        file: new File([JSON.stringify(chunkItems)], createChunkFileName(file.name, files.length + 1), {
          type: "application/json",
        }),
        recordCount: chunkItems.length,
      });
    }
    return {
      files,
      totalRecords: payload.length,
    };
  }

  if (payload && typeof payload === "object") {
    return {
      files: [
        {
          file: new File([JSON.stringify(payload)], createChunkFileName(file.name, 1), {
            type: "application/json",
          }),
          recordCount: 1,
        },
      ],
      totalRecords: 1,
    };
  }

  throw new Error("JSON 文件格式不正确，导入内容必须是对象或数组。");
}

export function ImportsPage() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const { data, isLoading } = useImportBatches();
  const initializeFolderUploadMutation = useInitializeImportFolderUpload();
  const uploadBatchChunkMutation = useUploadImportBatchChunk();
  const [fileList, setFileList] = useState<UploadListItem[]>([]);
  const [folderFiles, setFolderFiles] = useState<File[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<number | undefined>(undefined);
  const [importProgress, setImportProgress] = useState<ImportProgressState | null>(null);
  const dataSourceCode = Form.useWatch("data_source_code", form) as string | undefined;

  const batches = data ?? [];
  const detailQuery = useImportBatchDetail(selectedBatchId);
  const detail = detailQuery.data;
  const selectedBatch = detail?.batch ?? batches.find((item) => item.id === selectedBatchId);
  const singleFile = fileList[0]?.originFileObj;

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
  const largeJsonUploadMode = useMemo(
    () => shouldUseChunkedJsonUpload(dataSourceCode, singleFile),
    [dataSourceCode, singleFile],
  );
  const localProgressPercent = useMemo(() => {
    if (!importProgress) {
      return 0;
    }
    if (importProgress.totalRecords && importProgress.totalRecords > 0) {
      return Math.min(
        100,
        Math.round((importProgress.processedRecords / importProgress.totalRecords) * 100),
      );
    }
    if (importProgress.totalChunks <= 0) {
      return 0;
    }
    return Math.min(
      99,
      Math.round((Math.max(importProgress.currentChunk - 1, 0) / importProgress.totalChunks) * 100),
    );
  }, [importProgress]);
  const localProgressDescription = useMemo(() => {
    if (!importProgress) {
      return "";
    }
    if (importProgress.phase === "preparing") {
      return `正在解析并拆分 ${importProgress.fileName}，大文件首次准备可能需要几十秒。`;
    }
    const chunkSummary = `第 ${importProgress.currentChunk} / ${importProgress.totalChunks} 批`;
    if (typeof importProgress.totalRecords === "number") {
      if (importProgress.mode === "folder" || importProgress.mode === "single-file") {
        return `${chunkSummary}，已上传 ${importProgress.processedRecords} / ${importProgress.totalRecords} 个文件。`;
      }
      return `${chunkSummary}，已上传 ${importProgress.processedRecords} / ${importProgress.totalRecords} 条记录。`;
    }
    return `${chunkSummary}，文件正在上传到服务器。`;
  }, [importProgress]);
  const batchProgress = useMemo(() => {
    if (!selectedBatch || !isActiveImportStatus(selectedBatch.import_status)) {
      return null;
    }

    if (selectedBatch.import_status === "UPLOADING") {
      const totalFiles = selectedBatch.total_file_count || selectedBatch.uploaded_file_count || 1;
      const percent = Math.min(100, Math.round((selectedBatch.uploaded_file_count / totalFiles) * 100));
      return {
        title: "上传进度",
        percent,
        description: `已上传 ${selectedBatch.uploaded_file_count} / ${totalFiles} 个文件，上传完成后会自动进入后台处理。`,
        extra:
          selectedBatch.expected_records && selectedBatch.expected_records > 0
            ? `预计总记录数 ${selectedBatch.expected_records} 条。`
            : "大批量导入时可以先离开这个页面，稍后回来查看结果。",
      };
    }

    if (selectedBatch.import_status === "QUEUED") {
      return {
        title: "后台排队中",
        percent: 100,
        description: "文件上传已完成，后台任务正在排队启动。",
        extra: "页面会自动刷新，无需一直停留在这里等待。",
      };
    }

    const processedRecords = selectedBatch.total_records;
    const expectedRecords = selectedBatch.expected_records ?? undefined;
    const totalFiles = selectedBatch.total_file_count || selectedBatch.processed_file_count || 1;
    const progressBase = expectedRecords && expectedRecords > 0
      ? expectedRecords
      : totalFiles;
    const progressValue = expectedRecords && expectedRecords > 0
      ? processedRecords
      : selectedBatch.processed_file_count;
    const percent = Math.min(100, Math.round((progressValue / Math.max(progressBase, 1)) * 100));

    let etaText = "正在根据实际处理速度估算剩余时间。";
    if (
      selectedBatch.processing_started_at &&
      progressValue > 0 &&
      progressBase > progressValue
    ) {
      const startedAt = new Date(selectedBatch.processing_started_at).getTime();
      const elapsedSeconds = Math.max(1, (Date.now() - startedAt) / 1000);
      const remainingUnits = progressBase - progressValue;
      const secondsPerUnit = elapsedSeconds / progressValue;
      etaText = `预计剩余 ${formatDuration(remainingUnits * secondsPerUnit)}。`;
    } else if (progressBase > 0 && progressValue >= progressBase) {
      etaText = "已接近完成，正在收尾。";
    }

    const processedText =
      expectedRecords && expectedRecords > 0
        ? `已处理 ${processedRecords} / ${expectedRecords} 条记录`
        : `已处理 ${selectedBatch.processed_file_count} / ${totalFiles} 个文件`;

    return {
      title: "后台处理进度",
      percent,
      description: `${processedText}，${etaText}`,
      extra: `当前已完成 ${selectedBatch.processed_file_count} / ${totalFiles} 个文件分片处理。`,
    };
  }, [selectedBatch]);
  const isUploading =
    initializeFolderUploadMutation.isPending ||
    uploadBatchChunkMutation.isPending ||
    importProgress !== null;

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
    setImportProgress(null);

    if (!filteredFiles.length) {
      message.warning("当前文件夹里没有符合数据源要求的文件。");
      return;
    }

    message.success(`已选择文件夹，共识别 ${filteredFiles.length} 个可导入文件。`);
  };

  const handleUpload = async () => {
    const selectedDataSourceCode = form.getFieldValue("data_source_code") as string | undefined;

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

        const chunks = chunkItems(folderFiles, FOLDER_UPLOAD_CHUNK_SIZE);
        let uploadedFiles = 0;

        for (const [index, chunk] of chunks.entries()) {
          setImportProgress({
            mode: "folder",
            phase: "uploading",
            currentChunk: index + 1,
            totalChunks: chunks.length,
            processedRecords: uploadedFiles,
            totalRecords: folderFiles.length,
            fileName: folderName || "文件夹导入",
          });
          const result = await uploadBatchChunkMutation.mutateAsync({
            batchId: initBatch.id,
            files: chunk,
            finalize: index === chunks.length - 1,
          });
          uploadedFiles += chunk.length;
          setSelectedBatchId(result.batch.id);
        }

        setImportProgress(null);
        setFolderFiles([]);
        if (folderInputRef.current) {
          folderInputRef.current.value = "";
        }
        message.success("文件上传完成，后台正在处理中，可在下方查看实时进度。");
        return;
      }

      if (!singleFile) {
        message.warning("请先选择要上传的文件，或者选择一个文件夹。");
        return;
      }

      if (shouldUseChunkedJsonUpload(selectedDataSourceCode, singleFile)) {
        setImportProgress({
          mode: "large-json",
          phase: "preparing",
          currentChunk: 0,
          totalChunks: 0,
          processedRecords: 0,
          totalRecords: 0,
          fileName: singleFile.name,
        });
        await new Promise<void>((resolve) => {
          window.setTimeout(resolve, 0);
        });

        const prepared = await splitJsonFileIntoChunks(singleFile, LARGE_JSON_RECORD_CHUNK_SIZE);
        if (!prepared.totalRecords) {
          throw new Error("JSON 文件中没有可导入记录。");
        }

        const initBatch = await initializeFolderUploadMutation.mutateAsync({
          dataSourceCode: selectedDataSourceCode,
          folderName: `${singleFile.name}（自动拆分）`,
          fileCount: prepared.files.length,
          expectedRecords: prepared.totalRecords,
        });
        setSelectedBatchId(initBatch.id);

        const uploadGroups = chunkItems(prepared.files, LARGE_JSON_UPLOAD_REQUEST_CHUNK_SIZE);
        let uploadedRecords = 0;
        for (const [index, group] of uploadGroups.entries()) {
          setImportProgress({
            mode: "large-json",
            phase: "uploading",
            currentChunk: index + 1,
            totalChunks: uploadGroups.length,
            processedRecords: uploadedRecords,
            totalRecords: prepared.totalRecords,
            fileName: singleFile.name,
          });
          const result = await uploadBatchChunkMutation.mutateAsync({
            batchId: initBatch.id,
            files: group.map((item) => item.file),
            finalize: index === uploadGroups.length - 1,
          });
          uploadedRecords += group.reduce((sum, item) => sum + item.recordCount, 0);
          setSelectedBatchId(result.batch.id);
        }

        setImportProgress(null);
        setFileList([]);
        form.resetFields(["file"]);
        message.success("大文件上传完成，后台正在分批处理，可在下方查看已处理条数和预计剩余时间。");
        return;
      }

      const initBatch = await initializeFolderUploadMutation.mutateAsync({
        dataSourceCode: selectedDataSourceCode,
        folderName: singleFile.name,
        fileCount: 1,
      });
      setSelectedBatchId(initBatch.id);
      setImportProgress({
        mode: "single-file",
        phase: "uploading",
        currentChunk: 1,
        totalChunks: 1,
        processedRecords: 0,
        totalRecords: 1,
        fileName: singleFile.name,
      });
      const result = await uploadBatchChunkMutation.mutateAsync({
        batchId: initBatch.id,
        files: [singleFile],
        finalize: true,
      });
      setImportProgress(null);
      message.success("文件上传完成，后台正在处理中，可在下方查看进度。");
      setSelectedBatchId(result.batch.id);
      setFileList([]);
      form.resetFields(["file"]);
    } catch (error) {
      setImportProgress(null);
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
          对于超大的 dataset2 JSON 单文件，系统会自动拆分后分批导入，并在页面展示进度。
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
                    setImportProgress(null);
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
                      setImportProgress(null);
                      if (folderInputRef.current) {
                        folderInputRef.current.value = "";
                      }
                    }
                  }}
                >
                  <Button>选择文件</Button>
                </Upload>
                {largeJsonUploadMode ? (
                  <Typography.Text type="secondary">
                    已检测到大文件，点击“开始导入”后会先自动拆分成多个 JSON 分片，再逐批导入并显示进度。
                  </Typography.Text>
                ) : null}
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
                  {importProgress?.mode === "folder" ? (
                    <Typography.Text type="secondary">
                      正在上传：第 {importProgress.currentChunk} / {importProgress.totalChunks} 批
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
                {isUploading ? "导入中..." : "开始导入"}
              </Button>
            </Col>
          </Row>
        </Form>
      </Card>

      {importProgress ? (
        <Card>
          <Space direction="vertical" size={10} style={{ width: "100%" }}>
            <Typography.Text strong>
              {importProgress.mode === "large-json" ? "大文件上传进度" : "文件上传进度"}
            </Typography.Text>
            <Progress percent={localProgressPercent} status="active" />
            <Typography.Text>{localProgressDescription}</Typography.Text>
            <Typography.Text type="secondary">
              上传完成后会自动切换为后台处理，你可以继续留在本页查看进度，也可以稍后再回来。
            </Typography.Text>
          </Space>
        </Card>
      ) : null}

      {!importProgress && batchProgress ? (
        <Card>
          <Space direction="vertical" size={10} style={{ width: "100%" }}>
            <Typography.Text strong>{batchProgress.title}</Typography.Text>
            <Progress percent={batchProgress.percent} status="active" />
            <Typography.Text>{batchProgress.description}</Typography.Text>
            <Typography.Text type="secondary">{batchProgress.extra}</Typography.Text>
          </Space>
        </Card>
      ) : null}

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
              {detail.summary.matched_by_content_hash > 0 ? (
                <Button
                  onClick={() => navigate(`/imports/batches/${detail.batch.id}/content-hash-matches`)}
                >
                  查看内容指纹命中明细
                </Button>
              ) : null}
            </div>

            <Row gutter={[16, 16]}>
              <Col xs={24} md={6}>
                <Card>
                  <Statistic title="总文件片" value={detail.batch.total_file_count} />
                </Card>
              </Col>
              <Col xs={24} md={6}>
                <Card>
                  <Statistic title="已上传文件片" value={detail.batch.uploaded_file_count} />
                </Card>
              </Col>
              <Col xs={24} md={6}>
                <Card>
                  <Statistic title="已处理文件片" value={detail.batch.processed_file_count} />
                </Card>
              </Col>
              <Col xs={24} md={6}>
                <Card>
                  <Statistic title="预计总记录" value={detail.batch.expected_records ?? "-"} />
                </Card>
              </Col>
            </Row>

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
