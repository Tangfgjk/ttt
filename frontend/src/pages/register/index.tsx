import { LockOutlined, SafetyCertificateOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Space, Typography, message } from "antd";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuthStore } from "@/app/store/auth-store";
import { register } from "@/services/auth";

import { AuthShell, buildSessionFromAuthUser, resolvePostLoginPath } from "@/pages/login/auth-shared";

type RegisterForm = {
  username: string;
  password: string;
  confirm_password: string;
};

export function RegisterPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = async (values: RegisterForm) => {
    setSubmitting(true);
    try {
      const result = await register(values);
      setSession(buildSessionFromAuthUser(result.user));
      message.success(result.message);
      navigate(resolvePostLoginPath(result.user), { replace: true });
    } catch {
      message.error("注册失败，请检查输入信息后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="注册标注员账号"
      description="新注册账号默认为标注员，可直接进入培训准入流程。"
      foot={
        <>
          <Typography.Text type="secondary">
            已有账号？<Link to="/login">返回登录</Link>
          </Typography.Text>
          <Typography.Text type="secondary">
            账号密码遇到问题？<Link to="/forgot-password">查看找回方式</Link>
          </Typography.Text>
        </>
      }
    >
      <Alert
        type="info"
        showIcon
        icon={<SafetyCertificateOutlined />}
        className="auth-inline-alert"
        message="注册成功后会直接进入培训页，通过培训后即可开始标注。"
      />
      <Form<RegisterForm> layout="vertical" onFinish={handleFinish}>
        <Form.Item
          label="用户名"
          name="username"
          rules={[
            { required: true, message: "请输入用户名" },
            { min: 3, max: 20, message: "用户名长度需为 3-20 位" },
            {
              pattern: /^[A-Za-z0-9_\u4e00-\u9fa5]+$/,
              message: "用户名仅支持中文、字母、数字和下划线",
            },
          ]}
        >
          <Input
            size="large"
            prefix={<UserOutlined />}
            placeholder="例如：张三_初中"
            autoComplete="username"
          />
        </Form.Item>
        <Form.Item
          label="密码"
          name="password"
          rules={[
            { required: true, message: "请输入密码" },
            { min: 6, message: "密码至少为 6 位" },
          ]}
        >
          <Input.Password
            size="large"
            prefix={<LockOutlined />}
            placeholder="设置登录密码"
            autoComplete="new-password"
          />
        </Form.Item>
        <Form.Item
          label="确认密码"
          name="confirm_password"
          dependencies={["password"]}
          rules={[
            { required: true, message: "请再次输入密码" },
            ({ getFieldValue }: { getFieldValue: (name: string) => string }) => ({
              validator(_: unknown, value: string) {
                if (!value || getFieldValue("password") === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error("两次输入的密码不一致"));
              },
            }),
          ]}
        >
          <Input.Password
            size="large"
            prefix={<LockOutlined />}
            placeholder="再次输入密码"
            autoComplete="new-password"
          />
        </Form.Item>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Button loading={submitting} type="primary" htmlType="submit" block size="large">
            注册并进入培训
          </Button>
          <Button block size="large" onClick={() => navigate("/login")}>
            返回登录
          </Button>
        </Space>
      </Form>
    </AuthShell>
  );
}
