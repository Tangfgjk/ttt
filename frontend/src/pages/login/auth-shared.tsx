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

export function buildSessionFromAuthUser(user: AuthUser): UserSession {
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

export function resolvePostLoginPath(user: AuthUser) {
  if (user.role === "admin") {
    return "/admin/overview";
  }
  if (user.role === "annotator" && user.training_scope === "none") {
    return "/annotator-training";
  }
  return "/workspace";
}
