import { InfoCircleOutlined, UserOutlined } from "@ant-design/icons";
import { Alert, Button, Form, Input, Typography, message } from "antd";
import { useState } from "react";
import { Link } from "react-router-dom";

import { forgotPassword } from "@/services/auth";

import { AuthShell } from "@/pages/login/auth-shared";

type ForgotPasswordForm = {
  username: string;
};

export function ForgotPasswordPage() {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleFinish = async (values: ForgotPasswordForm) => {
    setSubmitting(true);
    try {
      const result = await forgotPassword(values);
      setSubmitted(true);
      message.success(result.message);
    } catch {
      message.error("提交失败，请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      title="忘记密码"
      description="当前版本采用管理员协助重置密码的方式处理账号找回。"
      foot={
        <Typography.Text type="secondary">
          想起密码了？<Link to="/login">返回登录</Link>
        </Typography.Text>
      }
    >
      <Alert
        type="warning"
        showIcon
        icon={<InfoCircleOutlined />}
        className="auth-inline-alert"
        message="提交用户名后，系统会提示你联系管理员完成密码重置。"
      />
      <Form<ForgotPasswordForm> layout="vertical" onFinish={handleFinish}>
        <Form.Item
          label="用户名"
          name="username"
          rules={[{ required: true, message: "请输入用户名" }]}
        >
          <Input
            size="large"
            prefix={<UserOutlined />}
            placeholder="输入需要找回的用户名"
            autoComplete="username"
          />
        </Form.Item>
        <Button loading={submitting} type="primary" htmlType="submit" block size="large">
          提交找回申请
        </Button>
      </Form>
      {submitted ? (
        <Alert
          type="success"
          showIcon
          className="auth-inline-alert auth-inline-alert--success"
          message="请联系系统管理员重置密码，重置后请使用临时密码登录并尽快修改。"
        />
      ) : null}
    </AuthShell>
  );
}
