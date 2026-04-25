import {
  AppstoreOutlined,
  BarChartOutlined,
  ExperimentOutlined,
  ImportOutlined,
  LogoutOutlined,
  SearchOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import {
  Avatar,
  Badge,
  Button,
  Input,
  Layout,
  Menu,
  Space,
  Tag,
  Typography,
} from "antd";
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
  { key: "/annotate", icon: <TeamOutlined />, label: "标注工作台", roles: ["annotator", "reviewer"] },
  { key: "/questions", icon: <SearchOutlined />, label: "统一题池", roles: ["admin", "annotator", "reviewer"] },
  { key: "/visualization", icon: <BarChartOutlined />, label: "可视化", roles: ["admin", "annotator", "reviewer"] },
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
  return menuItems.find((item) => item.key === pathname)?.label ?? "TTT 标注平台";
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
      <Sider width={256} theme="light" className="app-shell__sider">
        <div className="brand-block">
          <div className="brand-block__eyebrow">Junior Math Annotation</div>
          <Typography.Title level={4} className="brand-block__title">
            TTT 标注平台
          </Typography.Title>
          <Typography.Paragraph className="brand-block__desc">
            统一题池、判重、导入、标注与训练统一协同的开发工作台。
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
          <div>
            <Typography.Title level={3} className="page-title">
              {getPageTitle(location.pathname)}
            </Typography.Title>
            <Space size={8}>
              <Tag color="cyan">开发阶段</Tag>
              <Badge status="processing" text="不依赖 Nginx，本地由 Vite 代理 /api" />
            </Space>
          </div>

          <Space size={16}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="全局搜索题目、批次或任务"
              style={{ width: 280 }}
            />
            <Space size={10}>
              <Avatar>{session?.name.slice(0, 1) ?? "U"}</Avatar>
              <div>
                <div>{session?.name}</div>
                <Typography.Text type="secondary">
                  {session ? getRoleLabel(session.role) : ""}
                </Typography.Text>
              </div>
            </Space>
            <Button
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
