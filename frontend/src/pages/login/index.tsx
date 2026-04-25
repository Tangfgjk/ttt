import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Button, Card, Col, Form, Input, Row, Space, Typography, message } from "antd";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "@/app/store/auth-store";
import { login } from "@/services/auth";

type LoginForm = {
  username: string;
  password: string;
};

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
      });
      message.success(result.message);
      navigate(result.user.role === "admin" ? "/admin/overview" : "/workspace");
    } catch {
      message.error("登录失败，请检查用户名和密码");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <Row gutter={24} align="middle" justify="center">
        <Col xs={24} lg={11}>
          <div className="login-hero">
            <div className="login-hero__eyebrow">Core Competency Annotation</div>
            <Typography.Title className="login-hero__title">
              初中数学核心素养标注平台
            </Typography.Title>
            <Typography.Paragraph className="login-hero__desc">
              现在登录已经改为真实走后端数据库。系统会根据登录用户的角色自动区分用户端和管理端。
            </Typography.Paragraph>
            <Card size="small">
              <Typography.Text strong>开发账号</Typography.Text>
              <div>管理员：admin / admin123</div>
              <div>标注员：annotator / annotator123</div>
              <div>复核员：reviewer / reviewer123</div>
            </Card>
          </div>
        </Col>
        <Col xs={24} md={16} lg={8}>
          <Card className="login-card">
            <Typography.Title level={3}>进入系统</Typography.Title>
            <Typography.Paragraph type="secondary">
              当前项目按你的要求，开发阶段密码直接保存在数据库中并做明文比对，后续可以再切换为加密方案。
            </Typography.Paragraph>
            <Form<LoginForm>
              layout="vertical"
              initialValues={{
                username: "admin",
                password: "admin123",
              }}
              onFinish={handleFinish}
            >
              <Form.Item label="用户名或邮箱" name="username" rules={[{ required: true }]}>
                <Input prefix={<UserOutlined />} placeholder="输入用户名或邮箱" />
              </Form.Item>
              <Form.Item label="密码" name="password" rules={[{ required: true }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="输入密码" />
              </Form.Item>
              <Button loading={submitting} type="primary" htmlType="submit" block size="large">
                登录并进入工作台
              </Button>
            </Form>
            <Space direction="vertical" size={6} style={{ marginTop: 16 }}>
              <Typography.Text type="secondary">登录后跳转规则：</Typography.Text>
              <Typography.Text type="secondary">管理员会进入管理端首页。</Typography.Text>
              <Typography.Text type="secondary">
                标注员和复核员会进入用户端工作台。
              </Typography.Text>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
