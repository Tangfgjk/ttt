import { LockOutlined, UserOutlined } from "@ant-design/icons";
import { Button, Form, Input, Space, Typography, message } from "antd";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuthStore } from "@/app/store/auth-store";
import { login } from "@/services/auth";

import { AuthShell, buildSessionFromAuthUser, resolvePostLoginPath } from "./auth-shared";

type LoginForm = {
  username: string;
  password: string;
};

export function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async (values: LoginForm) => {
    setSubmitting(true);
    try {
      const result = await login(values);
      setSession(buildSessionFromAuthUser(result.user));
      message.success(result.message);
      const requestedPath =
        location.state && typeof location.state === "object" && "from" in location.state
          ? location.state.from
          : undefined;
      navigate(resolvePostLoginPath(result.user, requestedPath), { replace: true });
    } catch {
      message.error("登录失败，请检查用户名和密码");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="登录系统"
      description="使用已开通的账号登录，系统会按角色进入对应工作区。"
      foot={
        <>
          <Typography.Text type="secondary">
            还没有标注员账号？<Link to="/register">立即注册</Link>
          </Typography.Text>
          <Typography.Text type="secondary">
            忘记密码？<Link to="/forgot-password">找回方式</Link>
          </Typography.Text>
          {location.state && typeof location.state === "object" && "from" in location.state ? (
            <Typography.Text type="secondary">请先登录后继续访问系统页面。</Typography.Text>
          ) : null}
        </>
      }
    >
      <Form<LoginForm> layout="vertical" onFinish={handleFinish}>
        <Form.Item
          label="用户名"
          name="username"
          rules={[{ required: true, message: "请输入用户名" }]}
        >
          <Input
            size="large"
            prefix={<UserOutlined />}
            placeholder="输入用户名"
            autoComplete="username"
          />
        </Form.Item>
        <Form.Item
          label="密码"
          name="password"
          rules={[{ required: true, message: "请输入密码" }]}
        >
          <Input.Password
            size="large"
            prefix={<LockOutlined />}
            placeholder="输入密码"
            autoComplete="current-password"
          />
        </Form.Item>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Button loading={submitting} type="primary" htmlType="submit" block size="large">
            登录并进入系统
          </Button>
          <Button block size="large" onClick={() => navigate("/register")}>
            注册标注员账号
          </Button>
        </Space>
      </Form>
    </AuthShell>
  );
}
