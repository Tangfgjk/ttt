import { InfoCircleOutlined } from "@ant-design/icons";
import { Popover, Space, Typography } from "antd";

type CompetencyHelpPopoverProps = {
  name: string;
  definition?: string | null;
  focusTip?: string | null;
};

const LEVEL_HINTS = [
  { level: 0, label: "0级", description: "该素养基本不参与本题求解，或不需要单独标出。" },
  { level: 1, label: "1级", description: "有体现，但主要用于辅助理解、读图或局部步骤。" },
  { level: 2, label: "2级", description: "支撑关键求解过程，对完成题目有明显作用。" },
  { level: 3, label: "3级", description: "主导整题的理解、转化或求解路径，是核心素养。" },
];

export function CompetencyHelpPopover({
  name,
  definition,
  focusTip,
}: CompetencyHelpPopoverProps) {
  const content = (
    <Space direction="vertical" size={10} className="competency-help-popover">
      <div>
        <Typography.Text strong>{name}</Typography.Text>
        <Typography.Paragraph type="secondary" style={{ margin: "6px 0 0" }}>
          {definition || "暂未配置该素养的详细定义。"}
        </Typography.Paragraph>
      </div>
      {focusTip ? <div className="competency-help-popover__tip">{focusTip}</div> : null}
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
