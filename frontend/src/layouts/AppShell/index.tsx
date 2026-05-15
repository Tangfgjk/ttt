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
import { App, Avatar, Badge, Button, FloatButton, Input, Layout, Space, Tag, Typography } from "antd";
import type { ReactNode } from "react";
import { useMemo } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuthStore, type UserRole } from "@/app/store/auth-store";

const { Header, Sider, Content } = Layout;

type AppMenuChild = {
  key: string;
  label: string;
};

type AppMenuItem = {
  key: string;
  icon: ReactNode;
  label: string;
  roles: UserRole[];
  children?: AppMenuChild[];
};

const menuItems: AppMenuItem[] = [
  { key: "/workspace", icon: <AppstoreOutlined />, label: "我的工作台", roles: ["annotator", "reviewer"] },
  { key: "/annotator-training", icon: <SafetyCertificateOutlined />, label: "培训准入", roles: ["annotator"] },
  { key: "/annotate", icon: <TeamOutlined />, label: "标注工作台", roles: ["annotator"] },
  { key: "/annotation-history", icon: <ProfileOutlined />, label: "我的标注记录", roles: ["annotator"] },
  { key: "/review", icon: <SafetyCertificateOutlined />, label: "标注复核", roles: ["reviewer"] },
  { key: "/review-history", icon: <FileSearchOutlined />, label: "已复核题目", roles: ["reviewer"] },
  {
    key: "/admin/overview",
    icon: <AppstoreOutlined />,
    label: "项目总览",
    roles: ["admin"],
    children: [
      { key: "/admin/overview#overview-hero", label: "系统定位" },
      { key: "/admin/overview#overview-metrics", label: "标签体系" },
      { key: "/admin/overview#overview-definitions", label: "核心素养" },
      { key: "/admin/overview#overview-references", label: "标准依据" },
    ],
  },
  {
    key: "/imports",
    icon: <ImportOutlined />,
    label: "导入中心",
    roles: ["admin"],
    children: [
      { key: "/imports#imports-upload", label: "上传入口" },
      { key: "/imports#imports-progress", label: "导入进度" },
      { key: "/imports#imports-batches", label: "批次列表" },
      { key: "/imports#imports-detail", label: "批次详情" },
    ],
  },
  {
    key: "/dedup-review",
    icon: <SafetyCertificateOutlined />,
    label: "判重复核",
    roles: ["admin", "reviewer"],
    children: [
      { key: "/dedup-review#dedup-summary", label: "候选概览" },
      { key: "/dedup-review#dedup-bulk", label: "批量规则" },
      { key: "/dedup-review#dedup-candidates", label: "候选详情" },
    ],
  },
  {
    key: "/questions",
    icon: <SearchOutlined />,
    label: "统一题池",
    roles: ["admin"],
    children: [
      { key: "/questions#questions-overview", label: "题池概览" },
      { key: "/questions#questions-filters", label: "筛选条件" },
      { key: "/questions#questions-list", label: "题目列表" },
    ],
  },
  {
    key: "/visualization",
    icon: <BarChartOutlined />,
    label: "嵌入可视化",
    roles: ["admin"],
    children: [
      { key: "/visualization#visualization-status", label: "嵌入概览" },
      { key: "/visualization#visualization-chart", label: "分布图" },
      { key: "/visualization#visualization-detail", label: "选点详情" },
    ],
  },
  {
    key: "/label-insights",
    icon: <BarChartOutlined />,
    label: "标注结果分析",
    roles: ["admin"],
  },
  {
    key: "/admin",
    icon: <AppstoreOutlined />,
    label: "管理后台",
    roles: ["admin"],
    children: [
      { key: "/admin#admin-training", label: "训练模型" },
      { key: "/admin#admin-prediction", label: "低置信度选题" },
      { key: "/admin#admin-coreset", label: "CoreSet 选题" },
    ],
  },
  {
    key: "/training",
    icon: <ExperimentOutlined />,
    label: "训练监控",
    roles: ["admin"],
    children: [
      { key: "/training#training-summary", label: "运行概览" },
      { key: "/training#training-selection-batches", label: "题池治理" },
      { key: "/training#training-coreset-history", label: "CoreSet 历史" },
      { key: "/training#training-trends", label: "趋势分析" },
      { key: "/training#training-runs", label: "训练任务" },
      { key: "/training#training-models", label: "模型版本" },
      { key: "/training#training-prediction-runs", label: "预测任务" },
    ],
  },
];

function getRoleLabel(role: UserRole) {
  if (role === "admin") return "系统管理员";
  if (role === "annotator") return "标注员";
  return "复核员";
}

function getPageTitle(pathname: string) {
  return menuItems.find((item) => pathname.startsWith(item.key))?.label ?? "K12 学科标注平台";
}

function getSelectedMenuKey(pathname: string, hash: string, visibleItems: AppMenuItem[]) {
  const hashKey = `${pathname}${hash}`;
  if (hash) {
    const matchedChild = visibleItems.some((item) =>
      item.children?.some((child) => child.key === hashKey),
    );
    if (matchedChild) {
      return hashKey;
    }
  }
  return visibleItems.find((item) => pathname.startsWith(item.key))?.key ?? pathname;
}

function isMenuItemActive(item: AppMenuItem, selectedKey: string, pathname: string) {
  return (
    selectedKey === item.key ||
    item.children?.some((child) => child.key === selectedKey) ||
    pathname === item.key
  );
}

export function AppShell() {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const session = useAuthStore((state) => state.session);
  const logout = useAuthStore((state) => state.logout);

  const visibleMenuItems = useMemo(
    () => menuItems.filter((item) => session && item.roles.includes(session.role)),
    [session],
  );
  const selectedKey = getSelectedMenuKey(location.pathname, location.hash, visibleMenuItems);
  const handleNavigation = (key: string) => {
    const trainingScope = session?.trainingScope ?? "none";
    const needsTraining =
      session?.role === "annotator" &&
      trainingScope === "none" &&
      ["/annotate", "/annotation-history"].includes(key);

    if (needsTraining) {
      message.warning("请先完成培训准入，培训通过后才能进入标注工作台和我的标注记录。");
      navigate("/annotator-training");
      return;
    }

    navigate(key);
    if (!key.includes("#") && key === location.pathname) {
      window.requestAnimationFrame(() => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }
  };

  return (
    <Layout className="app-shell">
      <Sider width={264} theme="light" className="app-shell__sider">
        <div className="brand-block">
          <div className="brand-block__eyebrow">K12 Subject Annotation</div>
          <Typography.Title level={4} className="brand-block__title">
            K12 学科标注平台
          </Typography.Title>
          <Typography.Paragraph className="brand-block__desc">
            面向 K12 多学科题目的导入、判重、培训、标注与复核协同工作台。
          </Typography.Paragraph>
        </div>

        <nav className="app-nav" aria-label="Main navigation">
          {visibleMenuItems.map((item) => {
            const isActive = isMenuItemActive(item, selectedKey, location.pathname);
            return (
              <div
                key={item.key}
                className={`app-nav__group${isActive ? " app-nav__group--active" : ""}`}
              >
                <button
                  type="button"
                  className="app-nav__item"
                  onClick={() => handleNavigation(item.key)}
                  aria-current={isActive ? "page" : undefined}
                >
                  <span className="app-nav__icon">{item.icon}</span>
                  <span className="app-nav__label">{item.label}</span>
                  {item.children?.length ? <span className="app-nav__chevron" /> : null}
                </button>
                {item.children?.length ? (
                  <div className="app-nav__children">
                    {item.children.map((child) => (
                      <button
                        key={child.key}
                        type="button"
                        className={`app-nav__child${
                          child.key === selectedKey ? " app-nav__child--active" : ""
                        }`}
                        onClick={() => handleNavigation(child.key)}
                      >
                        {child.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </nav>
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
            <Input prefix={<SearchOutlined />} placeholder="全局搜索题目、批次或任务" className="app-shell__search" />
            <div className="app-shell__user">
              <Avatar className="app-shell__avatar">{session?.name.slice(0, 1) ?? "U"}</Avatar>
              <div className="app-shell__user-meta">
                <Typography.Text strong>{session?.name}</Typography.Text>
                <Typography.Text type="secondary">{session ? getRoleLabel(session.role) : ""}</Typography.Text>
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
        <FloatButton.BackTop visibilityHeight={320} className="app-back-top" />
      </Layout>
    </Layout>
  );
}
