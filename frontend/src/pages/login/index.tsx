import {
  ApartmentOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Button, Card, Col, Form, Input, Row, Space, Typography, message } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/app/store/auth-store";
import { login } from "@/services/auth";

type LoginForm = {
  username: string;
  password: string;
};

const devAccounts = [
  { label: "管理员", value: "admin / admin123" },
  { label: "标注员", value: "annotator / annotator123" },
  { label: "开发标注员 1", value: "annotator_dev_1 / annotator123" },
  { label: "开发标注员 2", value: "annotator_dev_2 / annotator123" },
  { label: "开发标注员 3", value: "annotator_dev_3 / annotator123" },
  { label: "复核员", value: "reviewer / reviewer123" },
];

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async (values: LoginForm) => {
    setSubmitting(true);
    try {
      const result = await login(values);
      setSession({
        id: result.user.id,
        username: result.user.username,
        email: result.user.email,
        name: result.user.real_name || result.user.username,
        role: result.user.role,
        isVerified: result.user.is_verified,
        trainingScope: result.user.training_scope,
      });
      message.success(result.message);
      navigate(
        result.user.role === "admin"
          ? "/admin/overview"
          : result.user.role === "annotator" && result.user.training_scope === "none"
            ? "/annotator-training"
            : "/workspace",
      );
    } catch {
      message.error("登录失败，请检查用户名和密码");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-shell">
        <Row gutter={[48, 32]} align="middle">
          <Col xs={24} lg={13}>
            <div className="login-hero">
              <div className="login-brand-mark">
                <ApartmentOutlined />
              </div>
              <div className="login-hero__eyebrow">K12 Subject Core Competency</div>
              <Typography.Title className="login-hero__title">
                K12 学科核心素养标注平台
              </Typography.Title>
              <Typography.Paragraph className="login-hero__desc">
                支持 K12 多学科题库导入、内容判重、人工标注、复核与训练数据管理。
              </Typography.Paragraph>
              <div className="login-feature-row">
                <span>
                  <DatabaseOutlined /> 多学科题库
                </span>
                <span>
                  <SafetyCertificateOutlined /> 内容判重
                </span>
                <span>
                  <CheckCircleOutlined /> 标注复核
                </span>
              </div>
              <div className="login-account-panel">
                <Typography.Text strong>开发账号</Typography.Text>
                <div className="login-account-list">
                  {devAccounts.map((item) => (
                    <div key={item.label} className="login-account-row">
                      <span className="login-account-row__label">{item.label}</span>
                      <code className="login-account-row__value">{item.value}</code>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Col>
          <Col xs={24} md={18} lg={10} xl={8}>
            <Card className="login-card">
              <div className="login-card__header">
                <Typography.Title level={3}>进入系统</Typography.Title>
                <Typography.Paragraph type="secondary">
                  使用账号登录后进入对应工作区。
                </Typography.Paragraph>
              </div>
              <Form<LoginForm>
                layout="vertical"
                initialValues={{
                  username: "admin",
                  password: "admin123",
                }}
                onFinish={handleFinish}
              >
                <Form.Item label="用户名或邮箱" name="username" rules={[{ required: true }]}>
                  <Input
                    size="large"
                    prefix={<UserOutlined />}
                    placeholder="输入用户名或邮箱"
                  />
                </Form.Item>
                <Form.Item label="密码" name="password" rules={[{ required: true }]}>
                  <Input.Password
                    size="large"
                    prefix={<LockOutlined />}
                    placeholder="输入密码"
                  />
                </Form.Item>
                <Button loading={submitting} type="primary" htmlType="submit" block size="large">
                  登录并进入工作台
                </Button>
              </Form>
              <Space className="login-card__foot" direction="vertical" size={4}>
                <Typography.Text type="secondary">
                  管理员进入管理端，标注员与复核员进入工作台。
                </Typography.Text>
              </Space>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
}
