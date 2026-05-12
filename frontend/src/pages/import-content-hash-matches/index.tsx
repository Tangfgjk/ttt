import { ArrowLeftOutlined } from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Result,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
} from "antd";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { QuestionRichText } from "@/components/question-rich-text";
import { useImportBatchDetail, useImportBatchRecords } from "@/modules/import-center/hooks";
import { useQuestionDetail } from "@/modules/question-bank/hooks";
import type { ImportSourceRecord } from "@/types/imports";

const DEFAULT_PAGE_SIZE = 20;

export function ImportContentHashMatchesPage() {
  const navigate = useNavigate();
  const params = useParams<{ batchId: string }>();
  const batchId = Number(params.batchId);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);

  const detailQuery = useImportBatchDetail(Number.isFinite(batchId) ? batchId : undefined);
  const recordsQuery = useImportBatchRecords(
    Number.isFinite(batchId) ? batchId : undefined,
    {
      parse_status: "MATCHED_BY_CONTENT_HASH",
      page,
      page_size: pageSize,
    },
  );
  const questionDetailQuery = useQuestionDetail(activeQuestionId);

  const batch = detailQuery.data?.batch;
  const summary = detailQuery.data?.summary;
  const records = recordsQuery.data?.items ?? [];
  const meta = recordsQuery.data?.meta;
  const currentPage = meta?.page ?? page;
  const currentPageSize = meta?.page_size ?? pageSize;
  const total = meta?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / currentPageSize));

  const columns = useMemo(
    () => [
      {
        title: "源记录键",
        dataIndex: "source_record_key",
        width: 220,
      },
      {
        title: "导入原题摘要",
        render: (_: unknown, record: ImportSourceRecord) => (
          <Typography.Paragraph ellipsis={{ rows: 3, expandable: false }} style={{ marginBottom: 0 }}>
            {record.source_preview ?? "-"}
          </Typography.Paragraph>
        ),
      },
      {
        title: "命中题目 ID",
        dataIndex: "normalized_question_id",
        width: 140,
        render: (value?: number | null) => value ?? "-",
      },
      {
        title: "命中题目摘要",
        render: (_: unknown, record: ImportSourceRecord) => (
          <Typography.Paragraph ellipsis={{ rows: 3, expandable: false }} style={{ marginBottom: 0 }}>
            {record.normalized_question_preview ?? "-"}
          </Typography.Paragraph>
        ),
      },
      {
        title: "操作",
        key: "actions",
        width: 120,
        render: (_: unknown, record: ImportSourceRecord) =>
          record.normalized_question_id ? (
            <Button type="link" onClick={() => setActiveQuestionId(record.normalized_question_id ?? null)}>
              查看题目
            </Button>
          ) : (
            "-"
          ),
      },
    ],
    [],
  );

  return (
    <>
      <Space direction="vertical" size={20} style={{ width: "100%" }}>
        <Card>
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/imports")} style={{ width: "fit-content" }}>
              返回导入中心
            </Button>
            <div>
              <Typography.Title level={3} style={{ marginTop: 0 }}>
                内容指纹命中明细
              </Typography.Title>
              <Typography.Paragraph type="secondary">
                这里展示当前批次中被判定为 `MATCHED_BY_CONTENT_HASH` 的导入记录，以及它们最终命中的统一题目。
              </Typography.Paragraph>
            </div>
            {batch ? (
              <Descriptions
                bordered
                size="small"
                column={2}
                items={[
                  { key: "batch_no", label: "批次号", children: batch.batch_no },
                  { key: "file_name", label: "文件标识", children: batch.file_name },
                  { key: "status", label: "批次状态", children: <Tag color="cyan">{batch.import_status}</Tag> },
                  {
                    key: "matched",
                    label: "内容指纹命中数",
                    children: summary?.matched_by_content_hash ?? 0,
                  },
                ]}
              />
            ) : null}
          </Space>
        </Card>

        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="内容指纹命中" value={summary?.matched_by_content_hash ?? 0} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="当前页 / 总页数" value={`${currentPage} / ${totalPages}`} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="当前页记录数" value={records.length} />
            </Card>
          </Col>
        </Row>

        <Card>
          {recordsQuery.isError ? (
            <Result
              status="warning"
              title="命中明细加载失败"
              subTitle={recordsQuery.error instanceof Error ? recordsQuery.error.message : "请稍后重试。"}
              extra={
                <Button type="primary" onClick={() => void recordsQuery.refetch()}>
                  重新加载
                </Button>
              }
            />
          ) : !recordsQuery.isLoading && !records.length ? (
            <Empty description="当前批次没有内容指纹命中记录。" />
          ) : (
            <Table<ImportSourceRecord>
              rowKey="id"
              loading={recordsQuery.isLoading || detailQuery.isLoading}
              columns={columns}
              dataSource={records}
              pagination={{
                current: currentPage,
                pageSize: currentPageSize,
                total,
                showSizeChanger: true,
                pageSizeOptions: ["20", "50", "100"],
                showTotal: (count: number, range: [number, number]) => `显示 ${range[0]}-${range[1]} 条，共 ${count} 条`,
                onChange: (nextPage: number, nextPageSize: number) => {
                  setPage(nextPage);
                  setPageSize(nextPageSize);
                },
              }}
              scroll={{ x: 1400 }}
            />
          )}
        </Card>
      </Space>

      <Drawer
        title={activeQuestionId ? `命中题目 #${activeQuestionId}` : "命中题目详情"}
        width={760}
        open={activeQuestionId !== null}
        onClose={() => setActiveQuestionId(null)}
      >
        {questionDetailQuery.isLoading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "48px 0" }}>
            <Spin />
          </div>
        ) : questionDetailQuery.isError ? (
          <Result
            status="warning"
            title="题目详情加载失败"
            subTitle={questionDetailQuery.error instanceof Error ? questionDetailQuery.error.message : "请稍后重试。"}
            extra={
              <Button type="primary" onClick={() => void questionDetailQuery.refetch()}>
                重新加载
              </Button>
            }
          />
        ) : questionDetailQuery.data ? (
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            <Descriptions
              bordered
              size="small"
              column={2}
              items={[
                { key: "id", label: "题目 ID", children: questionDetailQuery.data.id },
                { key: "subject", label: "学科", children: questionDetailQuery.data.subject.name },
                { key: "grade", label: "年级", children: questionDetailQuery.data.grade?.grade_name ?? "-" },
                { key: "type", label: "题型", children: questionDetailQuery.data.question_type?.name ?? "-" },
              ]}
            />
            <Card size="small" title="题干">
              <QuestionRichText
                html={questionDetailQuery.data.content?.stem_html}
                text={questionDetailQuery.data.content?.stem_text}
                emptyLabel="暂无题干"
              />
            </Card>
            <Card size="small" title="答案">
              <QuestionRichText text={questionDetailQuery.data.content?.answer_text} emptyLabel="暂无答案" />
            </Card>
            <Card size="small" title="解析">
              <QuestionRichText text={questionDetailQuery.data.content?.solution_text} emptyLabel="暂无解析" />
            </Card>
          </Space>
        ) : (
          <Empty description="暂无题目详情" />
        )}
      </Drawer>
    </>
  );
}
