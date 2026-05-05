# 本地跑通记录

记录日期：2026-05-05

## 本次目标

将项目在本机跑通，并连接外部 MySQL 数据库。

## 本地环境

- 后端：Python 3.11.9
- 前端：Node.js v24.15.0，npm 11.12.1
- 后端服务地址：http://127.0.0.1:8000
- 前端服务地址：http://127.0.0.1:5173
- 外部数据库：MySQL，库名 `competency_annotation_dev`

## 本次新增的本地文件

以下文件为本地运行配置，已被 `.gitignore` 忽略，不应提交：

- `backend/.env`
  - 配置 FastAPI 本地环境。
  - `DATABASE_URL` 指向外部 MySQL 的 `competency_annotation_dev`。
  - Redis/Celery 保持本地默认地址；当前 Web 服务启动和基础 API 验证不依赖 Redis 连接。
- `frontend/.env`
  - 配置 Vite 代理目标：`http://127.0.0.1:8000`。

## 本次修改的项目文件

- `frontend/package.json`
  - 新增开发依赖 `@types/node`，用于 Vite 配置文件的 Node 类型。
- `frontend/package-lock.json`
  - npm 安装依赖后自动更新。
- `frontend/tsconfig.node.json`
  - 将 Vite 配置侧 TypeScript 解析调整为 `Bundler`。
  - 补充 `target`、`lib`、`types`。
  - 开启依赖声明文件检查跳过项，避免 Vite/TypeScript 默认库声明互相检查导致构建失败。
- `backend/.gitignore`
  - 新增 `logs/`。
- `frontend/.gitignore`
  - 新增 `logs/`。

## 实际执行过的关键操作

后端：

```powershell
cd E:\ttt_tzk\ttt\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m pytest -q
```

前端：

```powershell
cd E:\ttt_tzk\ttt\frontend
npm.cmd install
npm.cmd install -D @types/node
npm.cmd run build
```

启动服务：

```powershell
cd E:\ttt_tzk\ttt\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

cd E:\ttt_tzk\ttt\frontend
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

当前我已用后台进程方式启动这两个服务，并将日志写入：

- `backend/logs/uvicorn.out.log`
- `backend/logs/uvicorn.err.log`
- `frontend/logs/vite.out.log`
- `frontend/logs/vite.err.log`

## 验证结果

后端测试：

```text
20 passed
```

前端构建：

```text
vite build succeeded
```

接口验证：

- `GET http://127.0.0.1:8000/api/v1/system/health` 返回 `status: ok`。
- `GET http://127.0.0.1:5173/api/v1/system/health` 可通过 Vite 代理转发到后端，并返回 `status: ok`。
- `POST http://127.0.0.1:8000/api/v1/auth/login` 使用开发账号 `admin / admin123` 登录成功。
- `GET http://127.0.0.1:5173/` 返回 Vite 前端页面。

## 注意事项

外部数据库当前的 Alembic 版本是 `20260503_0005`，而当前仓库代码内的 Alembic head 是 `20260425_0004`。因此：

- `alembic current` 会提示找不到 `20260503_0005`。
- 本次没有对外部数据库执行迁移或回退。
- 当前服务可以连接该外部库并完成健康检查、登录和前端代理验证。

另外，PowerShell 直接运行 `npm` 会受到执行策略影响，应使用 `npm.cmd`。
