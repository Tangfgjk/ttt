import {
  ApartmentOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { Card, Space, Typography } from "antd";
import type { ReactNode } from "react";

import type { UserSession } from "@/app/store/auth-store";
import type { AuthUser } from "@/types/auth";

type AuthShellProps = {
  title: string;
  description: string;
  children: ReactNode;
  foot?: ReactNode;
};

const featureItems = [
  { icon: <DatabaseOutlined />, label: "统一题库接入" },
  { icon: <SafetyCertificateOutlined />, label: "培训后准入标注" },
  { icon: <CheckCircleOutlined />, label: "标注与复核协同" },
];

export function AuthShell({ title, description, children, foot }: AuthShellProps) {
  return (
    <div className="login-page">
      <div className="login-shell">
        <div className="auth-grid">
          <div className="login-hero">
            <div className="login-brand-mark">
              <ApartmentOutlined />
            </div>
            <div className="login-hero__eyebrow">K12 Subject Core Competency</div>
            <Typography.Title className="login-hero__title">
              K12 学科核心素养标注平台
            </Typography.Title>
            <Typography.Paragraph className="login-hero__desc">
              面向 K12 多学科题目的导入、培训、标注、复核与训练治理平台。标注员注册后可直接进入培训准入流程，完成培训后再开始正式标注。
            </Typography.Paragraph>
            <div className="login-feature-row">
              {featureItems.map((item) => (
                <span key={item.label}>
                  {item.icon}
                  {item.label}
                </span>
              ))}
            </div>
            <div className="auth-highlight-panel">
              <div className="auth-highlight-panel__title">使用说明</div>
              <ul className="auth-highlight-list">
                <li>系统管理员与复核员账号由系统统一维护。</li>
                <li>页面注册仅开放给标注员，新账号注册后即可登录。</li>
                <li>未完成培训的标注员会优先进入培训页，培训通过后解锁标注工作台。</li>
              </ul>
            </div>
          </div>

          <Card className="login-card">
            <div className="login-card__header">
              <Typography.Title level={3}>{title}</Typography.Title>
              <Typography.Paragraph type="secondary">{description}</Typography.Paragraph>
            </div>
            {children}
            {foot ? (
              <Space className="login-card__foot" direction="vertical" size={4}>
                {foot}
              </Space>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}

type NewUserSession = Omit<UserSession, "issuedAt" | "expiresAt">;

const roleAllowedPathPrefixes = {
  admin: [
    "/admin",
    "/admin/overview",
    "/imports",
    "/questions",
    "/visualization",
    "/label-insights",
    "/training",
    "/dedup-review",
  ],
  annotator: ["/workspace", "/annotator-training", "/annotate", "/annotation-history"],
  reviewer: ["/workspace", "/review", "/review-history", "/dedup-review"],
} satisfies Record<AuthUser["role"], string[]>;

function isSafeRelativePath(path?: unknown): path is string {
  return typeof path === "string" && path.startsWith("/") && !path.startsWith("//") && !path.includes("://");
}

function canAccessPath(user: AuthUser, path: string) {
  if (path === "/") return true;
  if (path === "/login" || path === "/register" || path === "/forgot-password") return false;
  if (user.role === "annotator" && user.training_scope === "none") {
    return path.startsWith("/annotator-training");
  }
  return roleAllowedPathPrefixes[user.role].some((prefix) => path === prefix || path.startsWith(`${prefix}/`) || path.startsWith(`${prefix}#`));
}

export function buildSessionFromAuthUser(user: AuthUser): NewUserSession {
  return {
    id: user.id,
    username: user.username,
    email: user.email ?? null,
    name: user.real_name || user.username,
    role: user.role,
    isVerified: user.is_verified,
    trainingScope: user.training_scope,
    mustChangePassword: user.must_change_password ?? false,
  };
}

export function resolvePostLoginPath(user: AuthUser, requestedPath?: unknown) {
  if (isSafeRelativePath(requestedPath) && canAccessPath(user, requestedPath)) {
    return requestedPath === "/" ? defaultRolePath(user) : requestedPath;
  }
  return defaultRolePath(user);
}

function defaultRolePath(user: AuthUser) {
  if (user.role === "admin") {
    return "/admin/overview";
  }
  if (user.role === "annotator" && user.training_scope === "none") {
    return "/annotator-training";
  }
  return "/workspace";
}
