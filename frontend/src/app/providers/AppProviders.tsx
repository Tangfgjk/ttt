import { ConfigProvider, App as AntdApp, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PropsWithChildren, useState } from "react";

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
            staleTime: 30_000,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: "#047481",
            colorInfo: "#0f6f94",
            colorSuccess: "#17803d",
            colorWarning: "#b7791f",
            borderRadius: 8,
            colorBgLayout: "#eef4f7",
            colorBgContainer: "#ffffff",
            colorText: "#17252f",
            fontFamily:
              "'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
          },
        }}
      >
        <AntdApp>{children}</AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
