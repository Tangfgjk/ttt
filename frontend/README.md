# Frontend

当前前端采用前后端分离模式，但开发阶段不依赖 `Nginx`。

## 技术栈

- `React 18`
- `TypeScript`
- `Vite`
- `Ant Design`
- `TanStack Query`
- `Zustand`
- `Axios`
- `ECharts`

## 本地开发方式

1. 安装依赖

```bash
npm install
```

2. 启动前端

```bash
npm run dev
```

3. 前端会通过 Vite 代理把 `/api` 转发到后端

默认代理目标：

- `http://127.0.0.1:8000`

可通过 `.env` 覆盖：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

## 当前页面骨架

- `/login`
- `/`
- `/questions`
- `/imports`
- `/annotate`
- `/visualization`
- `/training`
- `/admin`

## 当前约束

- 登录页当前已接真实后端登录接口
- 当前开发账号会在首次登录时自动初始化：
  - `admin / admin123`
  - `annotator / annotator123`
  - `reviewer / reviewer123`
- 题库页和导入页已经按现有后端接口预接
- 标注页目前是工作台骨架，等后端标注闭环完成后继续接写接口
