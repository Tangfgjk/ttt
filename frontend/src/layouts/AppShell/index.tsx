import {
  AppstoreOutlined,
  BarChartOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  ImportOutlined,
  LogoutOutlined,
  ProfileOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Avatar, Badge, Button, Input, Layout, Menu, Space, Tag, Typography } from "antd";
import type { ReactNode } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuthStore, type UserRole } from "@/app/store/auth-store";

const { Header, Sider, Content } = Layout;

type MenuItem = {
  key: string;
  icon: ReactNode;
  label: string;
  roles: UserRole[];
};

const menuItems: MenuItem[] = [
  { key: "/workspace", icon: <AppstoreOutlined />, label: "我的工作台", roles: ["annotator", "reviewer"] },
  { key: "/annotator-training", icon: <SafetyCertificateOutlined />, label: "培训准入", roles: ["annotator"] },
  { key: "/annotate", icon: <TeamOutlined />, label: "标注工作台", roles: ["annotator"] },
  { key: "/annotation-history", icon: <ProfileOutlined />, label: "我的标注记录", roles: ["annotator"] },
  { key: "/review", icon: <SafetyCertificateOutlined />, label: "标注复核", roles: ["reviewer"] },
  { key: "/review-history", icon: <FileSearchOutlined />, label: "已复核题目", roles: ["reviewer"] },
  { key: "/dedup-review", icon: <SafetyCertificateOutlined />, label: "判重复核", roles: ["admin", "reviewer"] },
  { key: "/questions", icon: <SearchOutlined />, label: "统一题池", roles: ["admin"] },
  { key: "/visualization", icon: <BarChartOutlined />, label: "可视化", roles: ["admin"] },
  { key: "/admin/overview", icon: <AppstoreOutlined />, label: "项目总览", roles: ["admin"] },
  { key: "/imports", icon: <ImportOutlined />, label: "导入中心", roles: ["admin"] },
  { key: "/training", icon: <ExperimentOutlined />, label: "训练监控", roles: ["admin"] },
  { key: "/admin", icon: <AppstoreOutlined />, label: "管理后台", roles: ["admin"] },
];

function getRoleLabel(role: UserRole) {
  if (role === "admin") return "管理员";
  if (role === "annotator") return "标注员";
  return "复核员";
}

function getPageTitle(pathname: string) {
  return menuItems.find((item) => pathname.startsWith(item.key))?.label ?? "K12 学科核心素养标注平台";
}

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const session = useAuthStore((state) => state.session);
  const logout = useAuthStore((state) => state.logout);

  const visibleMenuItems = menuItems.filter((item) => session && item.roles.includes(session.role));
  const selectedKey =
    visibleMenuItems.find((item) => location.pathname.startsWith(item.key))?.key ?? location.pathname;

  return (
    <Layout className="app-shell">
      <Sider width={248} theme="light" className="app-shell__sider">
        <div className="brand-block">
          <div className="brand-block__eyebrow">K12 Subject Annotation</div>
          <Typography.Title level={4} className="brand-block__title">
            K12 学科标注平台
          </Typography.Title>
          <Typography.Paragraph className="brand-block__desc">
            面向 K12 多学科题目的导入、判重、培训、标注与复核协同工作台。
          </Typography.Paragraph>
        </div>

        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={visibleMenuItems.map((item) => ({
            key: item.key,
            icon: item.icon,
            label: item.label,
          }))}
          onClick={({ key }: { key: string }) => navigate(key)}
        />
      </Sider>

      <Layout>
        <Header className="app-shell__header">
          <div className="app-shell__header-main">
            <Typography.Title level={3} className="page-title">
              {getPageTitle(location.pathname)}
            </Typography.Title>
            <Space size={8} wrap>
              <Tag color="cyan">开发阶段</Tag>
              <Badge status="processing" text="K12 多学科题库标注与复核" />
            </Space>
          </div>

          <Space size={14} className="app-shell__header-actions">
            <Input
              prefix={<SearchOutlined />}
              placeholder="全局搜索题目、批次或任务"
              className="app-shell__search"
            />
            <div className="app-shell__user">
              <Avatar className="app-shell__avatar">{session?.name.slice(0, 1) ?? "U"}</Avatar>
              <div className="app-shell__user-meta">
                <Typography.Text strong>{session?.name}</Typography.Text>
                <Typography.Text type="secondary">
                  {session ? getRoleLabel(session.role) : ""}
                </Typography.Text>
              </div>
            </div>
            <Button
              className="app-shell__logout"
              icon={<LogoutOutlined />}
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              退出
            </Button>
          </Space>
        </Header>

        <Content className="app-shell__content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
