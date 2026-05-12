import { InfoCircleOutlined } from "@ant-design/icons";
import { Popover, Space, Tag, Typography } from "antd";

type CompetencyHelpPopoverProps = {
  name: string;
  definition?: string | null;
  focusTip?: string | null;
};

const LEVEL_HINTS = [
  { level: 0, label: "0级", description: "不体现这个素养，或不是这道题的核心关注点。" },
  { level: 1, label: "1级", description: "有体现，但更多是辅助理解或局部步骤。" },
  { level: 2, label: "2级", description: "支撑关键求解过程，对作答有明显作用。" },
  { level: 3, label: "3级", description: "决定整题理解或求解路径，是核心驱动力。" },
];

export function CompetencyHelpPopover({
  name,
  definition,
  focusTip,
}: CompetencyHelpPopoverProps) {
  const content = (
    <Space direction="vertical" size={10} style={{ maxWidth: 340 }}>
      <div>
        <Typography.Text strong>{name}</Typography.Text>
        <Typography.Paragraph type="secondary" style={{ margin: "6px 0 0" }}>
          {definition || "暂未配置该素养的详细定义。"}
        </Typography.Paragraph>
      </div>
      {focusTip ? <Tag color="processing">{focusTip}</Tag> : null}
      <Space direction="vertical" size={6}>
        {LEVEL_HINTS.map((item) => (
          <Typography.Text key={item.level}>
            <Typography.Text strong>{item.label}</Typography.Text>
            {"："}
            {item.description}
          </Typography.Text>
        ))}
      </Space>
    </Space>
  );

  return (
    <Popover content={content} trigger="hover" placement="topLeft">
      <Space size={4} className="competency-help-trigger">
        <Typography.Text strong>{name}</Typography.Text>
        <InfoCircleOutlined className="competency-help-trigger__icon" />
      </Space>
    </Popover>
  );
}
