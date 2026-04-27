import { ClockCircleOutlined, SaveOutlined, SendOutlined } from "@ant-design/icons";
import { Button, Card, Col, Empty, List, Radio, Row, Space, Tag, Typography } from "antd";

import { useQuestionList } from "@/modules/question-bank/hooks";
import type { QuestionListItem } from "@/types/question";

const competencyRows = [
  "抽象能力",
  "运算能力",
  "几何直观",
  "空间观念",
  "推理能力",
  "数据观念",
  "模型观念",
  "应用意识",
  "创新意识",
];

export function AnnotatePage() {
  const { data, isLoading } = useQuestionList({ page: 1, page_size: 20 });
  const activeQuestion = data?.items[0];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={8}>
        <Card title="待处理题目">
          {!isLoading && !data?.items.length ? (
            <Empty description="当前没有可展示的题目" />
          ) : (
            <List
              dataSource={data?.items ?? []}
              renderItem={(item: QuestionListItem) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <Space>
                        <span>题目 #{item.id}</span>
                        <Tag color="cyan">{item.annotation_status}</Tag>
                      </Space>
                    }
                    description={item.content?.stem_text?.slice(0, 48) ?? "暂无题干"}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      </Col>

      <Col xs={24} xl={16}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Card
            title="标注工作台"
            extra={
              <Space>
                <Tag color="gold">工作台骨架</Tag>
                <Tag icon={<ClockCircleOutlined />} color="default">
                  等待后端标注闭环
                </Tag>
              </Space>
            }
          >
            <Typography.Paragraph>
              {activeQuestion?.content?.stem_text ??
                "当前还没有真实题目进入统一题池，所以这里先展示工作台骨架。"}
            </Typography.Paragraph>
          </Card>

          <Card title="核心素养矩阵">
            <Space direction="vertical" size={14} style={{ width: "100%" }}>
              {competencyRows.map((item) => (
                <div key={item} className="matrix-row">
                  <Typography.Text strong>{item}</Typography.Text>
                  <Radio.Group
                    options={[
                      { label: "0", value: 0 },
                      { label: "1", value: 1 },
                      { label: "2", value: 2 },
                      { label: "3", value: 3 },
                    ]}
                    optionType="button"
                    buttonStyle="solid"
                  />
                </div>
              ))}
            </Space>
          </Card>

          <Card>
            <Space>
              <Button icon={<SaveOutlined />}>保存草稿</Button>
              <Button type="primary" icon={<SendOutlined />}>
                提交标注
              </Button>
            </Space>
          </Card>
        </Space>
      </Col>
    </Row>
  );
}
