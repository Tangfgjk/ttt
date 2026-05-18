import { Card, Descriptions, Empty, Segmented, Space, Tag, Typography } from "antd";
import { useState } from "react";

import { QuestionRichText } from "@/components/question-rich-text";
import { getAnnotationStatusColor, getAnnotationStatusLabel } from "@/constants/annotation-status";
import type { QuestionDetail } from "@/types/question";

type DetailViewMode = "rendered" | "raw";

function RawTextBlock({ value, emptyLabel = "暂无内容" }: { value?: string | null; emptyLabel?: string }) {
  if (!value) {
    return <Typography.Text type="secondary">{emptyLabel}</Typography.Text>;
  }
  return <pre className="question-raw-block">{value}</pre>;
}

function renderDifficultyStats(detail: QuestionDetail) {
  if (!detail.difficulty_level_stats.length) {
    return <Typography.Text type="secondary">暂无难度等级统计</Typography.Text>;
  }

  return (
    <Space size={[8, 8]} wrap>
      {detail.difficulty_level_stats.map((item) => (
        <Tag key={item.level} color={detail.source_difficulty_level === item.level ? "processing" : "default"}>
          {`L${item.level} · ${item.question_count}题`}
        </Tag>
      ))}
    </Space>
  );
}

export function QuestionDetailSections({ detail }: { detail: QuestionDetail }) {
  const [viewMode, setViewMode] = useState<DetailViewMode>("rendered");
  const isRawMode = viewMode === "raw";

  return (
    <Space direction="vertical" size={16} style={{ width: "100%" }}>
      <Space style={{ justifyContent: "space-between", width: "100%" }} wrap>
        <Typography.Title level={5} style={{ margin: 0 }}>
          题目详情
        </Typography.Title>
        <Segmented
          options={[
            { label: "渲染视图", value: "rendered" },
            { label: "原始文本", value: "raw" },
          ]}
          value={viewMode}
          onChange={(value: string | number) => setViewMode(value as DetailViewMode)}
        />
      </Space>

      <Descriptions
        title="基础信息"
        bordered
        size="small"
        column={2}
        items={[
          { key: "id", label: "题目 ID", children: detail.id },
          { key: "subject", label: "学科", children: detail.subject.name },
          { key: "grade", label: "年级", children: detail.grade?.grade_name ?? "-" },
          { key: "type", label: "题型", children: detail.question_type?.name ?? "-" },
          {
            key: "annotation_status",
            label: "标注状态",
            children: (
              <Tag color={getAnnotationStatusColor(detail.annotation_status)}>
                {getAnnotationStatusLabel(detail.annotation_status)}
              </Tag>
            ),
          },
          { key: "source_status", label: "来源状态", children: detail.source_status },
          { key: "difficulty", label: "难度", children: detail.difficulty_level ?? "-" },
          ...(detail.source_difficulty_level !== null && detail.source_difficulty_level !== undefined
            ? [
                {
                  key: "source_difficulty",
                  label: "原始难度标签",
                  children: detail.source_difficulty_level,
                },
              ]
            : []),
          { key: "blank_count", label: "填空数量", children: detail.blank_count },
          { key: "annotation_count", label: "已标注人数", children: detail.annotation_count },
          { key: "required_annotations", label: "要求标注人数", children: detail.required_annotations },
        ]}
      />

      <Card size="small" title="难度等级统计">
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          <Typography.Text type="secondary">
            当前系统内已出现的难度标签，用来对照原始数据中的难度值。
          </Typography.Text>
          {renderDifficultyStats(detail)}
        </Space>
      </Card>

      <Card size="small" title="完整题干">
        {isRawMode ? (
          <RawTextBlock value={detail.content?.stem_text} emptyLabel="暂无题干" />
        ) : (
          <QuestionRichText
            html={detail.content?.stem_html}
            text={detail.content?.stem_text}
            emptyLabel="暂无题干"
          />
        )}
      </Card>

      {isRawMode && detail.content?.stem_html ? (
        <Card size="small" title="原始 HTML">
          <RawTextBlock value={detail.content.stem_html} emptyLabel="暂无 HTML 内容" />
        </Card>
      ) : null}

      <Card size="small" title="答案">
        {isRawMode ? <RawTextBlock value={detail.content?.answer_text} /> : <QuestionRichText text={detail.content?.answer_text} />}
      </Card>

      <Card size="small" title="解析">
        {isRawMode ? (
          <RawTextBlock value={detail.content?.solution_text} />
        ) : (
          <QuestionRichText text={detail.content?.solution_text} />
        )}
      </Card>

      <Card size="small" title="知识点">
        {detail.knowledge_points.length ? (
          <Space size={[8, 8]} wrap>
            {detail.knowledge_points.map((item) => (
              <Tag key={item.id} color={item.is_core ? "processing" : "default"}>
                {item.knowledge_point_name}
              </Tag>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无知识点信息" />
        )}
      </Card>

      <Card size="small" title="目录信息">
        {detail.catalogs.length ? (
          <Space direction="vertical" size={8} style={{ width: "100%" }}>
            {detail.catalogs.map((item) => (
              <Typography.Text key={item.id}>
                {item.catalog_name}
                {item.school_code ? `（school_code: ${item.school_code}）` : ""}
              </Typography.Text>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无目录信息" />
        )}
      </Card>

      <Card size="small" title="外部来源映射">
        {detail.external_refs.length ? (
          <Space direction="vertical" size={10} style={{ width: "100%" }}>
            {detail.external_refs.map((item) => (
              <div key={item.id}>
                <Typography.Text strong>{item.data_source_name}</Typography.Text>
                <Typography.Text type="secondary"> / {item.data_source_code}</Typography.Text>
                <Typography.Text code style={{ marginLeft: 8 }}>
                  {item.external_question_id}
                </Typography.Text>
                {item.is_primary ? <Tag color="green" style={{ marginLeft: 8 }}>主映射</Tag> : null}
              </div>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无来源映射" />
        )}
      </Card>
    </Space>
  );
}
