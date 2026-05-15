# V7 Docker Compose 实施草案

更新时间：`2026-05-15`

## 1. 文档目的

本文档在《V7-Docker Compose 部署设计方案》的基础上，继续向“可实施”方向细化，目标是明确：

- `docker-compose.yml` 应包含哪些服务和关键字段
- `backend` / `worker` 镜像的 Dockerfile 应如何组织
- Nginx 配置需要覆盖哪些生产访问场景
- `.env.example` 应整理哪些关键环境变量
- 一台新服务器从零开始部署时的步骤顺序是什么

本文档仍然不直接提交部署代码文件，但已经尽量靠近后续实际落地所需的结构化草案。

## 2. 实施目标

本实施草案面向以下目标：

1. 让当前系统具备“从本地开发版切换到服务器常驻服务版”的明确实施路线
2. 让项目在换到另一台服务器时，能够通过固定步骤快速复现运行环境
3. 让后续真正编写 `docker-compose.yml`、Dockerfile、Nginx 配置时有统一参照

当前优先目标仍然是内网多人可用部署，而不是一步到位的公网正式生产化。

## 3. 推荐部署资产清单

建议后续补齐的部署资产如下：

```text
deploy/
├── docker/
│   ├── backend/
│   │   └── Dockerfile
│   ├── nginx/
│   │   └── default.conf
│   └── frontend/
│       └── Dockerfile            # 可选，前期可暂不落地
└── compose/
    ├── docker-compose.yml
    ├── .env
    └── .env.example
```

其中：

- `docker-compose.yml` 是服务编排主文件
- `.env.example` 是部署变量模板
- `backend/Dockerfile` 用于构建 backend / worker 共用镜像
- `nginx/default.conf` 用于生产静态托管和 API 反代

## 4. docker-compose.yml 草案结构

### 4.1 服务清单

第一版 Compose 建议包含以下 5 个核心服务：

- `mysql`
- `redis`
- `backend`
- `worker`
- `nginx`

后续如需进一步自动化前端构建，可选增加：

- `frontend-builder`

但对当前项目来说，前端先由发布流程构建 `dist` 再挂给 Nginx，会更简单。

### 4.2 顶层结构建议

`docker-compose.yml` 建议包含这些顶层块：

```yaml
services:
  mysql:
  redis:
  backend:
  worker:
  nginx:

volumes:
  mysql-data:
  redis-data:
  uploads-data:
  artifacts-data:

networks:
  ttt-net:
```

如果模型目录使用宿主机目录直接挂载，则不一定需要单独定义 `model-data` volume。

### 4.3 mysql 草案要求

`mysql` 服务建议至少包含：

- `image`
- `container_name`（可选）
- `restart`
- `environment`
- `volumes`
- `healthcheck`
- `networks`

推荐职责：

- 仅在 Docker 内部网络提供数据库服务
- 不直接暴露给公网
- 使用持久化数据卷

推荐关注点：

- 数据库名
- 业务账号
- root 密码
- 时区
- 字符集

### 4.4 redis 草案要求

`redis` 服务建议至少包含：

- `image`
- `restart`
- `command`（可选，按需开启持久化策略）
- `volumes`
- `healthcheck`
- `networks`

推荐职责：

- 只服务于 backend 和 worker
- 作为 Celery broker 与 result backend

### 4.5 backend 草案要求

`backend` 服务建议至少包含：

- `build`
- `env_file`
- `depends_on`
- `restart`
- `volumes`
- `command`
- `networks`

推荐挂载：

- 宿主机上传目录 -> `/data/uploads`
- 宿主机训练产物目录 -> `/data/artifacts`
- 宿主机模型目录 -> `/data/models`

推荐启动命令：

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

第一版可以不做多 worker 优化，先以清晰稳定为主。

### 4.6 worker 草案要求

`worker` 服务建议至少包含：

- `build`
- `env_file`
- `depends_on`
- `restart`
- `volumes`
- `command`
- `networks`

与 backend 的主要区别只有启动命令。

推荐启动方向：

- 启 Celery worker
- 和 backend 共享同一镜像、同一环境变量、同一挂载目录

设计原因：

- 代码只维护一份
- 部署和排查更简单
- 后续扩容 worker 比较方便

### 4.7 nginx 草案要求

`nginx` 服务建议至少包含：

- `image` 或 `build`
- `restart`
- `ports`
- `depends_on`
- `volumes`
- `networks`

它需要挂载：

- 前端 `dist` 目录
- Nginx 配置文件

推荐对外暴露：

- `80:80`

如果以后加 HTTPS，再扩展 `443:443`。

## 5. Volume 与挂载草案

### 5.1 推荐宿主机目录

在服务器上建议统一准备以下目录：

```text
/opt/ttt/
├── uploads/
├── artifacts/
├── models/
├── logs/
├── mysql/
└── redis/
```

### 5.2 推荐容器内路径

```text
/data/uploads
/data/artifacts
/data/models
/data/logs
```

### 5.3 挂载建议

建议映射关系如下：

| 宿主机目录 | 容器内路径 | 用途 |
| --- | --- | --- |
| `/opt/ttt/uploads` | `/data/uploads` | 导入文件与运行时上传内容 |
| `/opt/ttt/artifacts` | `/data/artifacts` | 主动学习、训练产物、中间结果 |
| `/opt/ttt/models` | `/data/models` | embedding 模型或训练模型 |
| `/opt/ttt/mysql` | MySQL 数据目录 | 业务数据库 |
| `/opt/ttt/redis` | Redis 数据目录 | Redis 数据 |

### 5.4 特别建议

模型目录建议使用宿主机路径直接挂载，而不要打进镜像。原因有三点：

- 模型文件体积大
- 模型更新频率和业务代码不同步
- 重新打镜像的成本更高

## 6. .env.example 草案清单

### 6.1 基础应用变量

```env
APP_NAME=TTT Annotation Backend
APP_ENV=prod
APP_DEBUG=false
ENABLE_DOCS=false
API_V1_PREFIX=/api/v1
```

### 6.2 数据库与 Redis 变量

```env
DATABASE_URL=mysql+pymysql://ttt_user:strong_password@mysql:3306/ttt_prod
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

MYSQL_DATABASE=ttt_prod
MYSQL_USER=ttt_user
MYSQL_PASSWORD=strong_password
MYSQL_ROOT_PASSWORD=strong_root_password
```

### 6.3 文件与模型路径变量

```env
IMPORT_UPLOAD_DIR=/data/uploads/imports
EMBEDDING_MODEL_PATH=/data/models/math_mlm_model
ACTIVE_LEARNING_CHECKPOINT_DIR=/data/artifacts/active_learning
```

### 6.4 可选扩展变量

```env
EMBEDDING_MODEL_CODE=math-roberta-mlm-v1
EMBEDDING_MODEL_NAME=Math Roberta MLM
EMBEDDING_BATCH_SIZE=16
VISUALIZATION_MAX_POINTS=50000
ACTIVE_LEARNING_TORCH_THREADS=1
```

### 6.5 当前项目需要特别清理的变量来源

从当前仓库现状看，后续需要重点从生产配置中移除以下本机耦合痕迹：

- `C:/Users/...`
- `D:/...`
- 开发机专用 Python 解释器路径
- 本地固定端口代理思路

所有这类配置都应统一替换为：

- 容器内路径
- Compose 服务名
- 可迁移的 `.env` 变量

## 7. backend Dockerfile 草案

### 7.1 目标

用一份 Dockerfile 同时支撑：

- `backend`
- `worker`

### 7.2 建议结构

`backend/Dockerfile` 建议包含以下逻辑：

1. 选择 `python:3.11-slim` 作为基础镜像
2. 安装必要系统依赖
3. 设置工作目录，例如 `/app`
4. 复制 `backend/` 代码
5. 安装 Python 依赖
6. 设置默认环境变量或最小运行上下文
7. 默认命令由 Compose 覆盖

### 7.3 设计原则

- 不在 Dockerfile 中写死数据库、Redis、模型目录路径
- 不写死本机开发路径
- 不将大模型直接复制进镜像
- 不在镜像中使用 `--reload`

### 7.4 backend 与 worker 的区分方式

通过 Compose 中不同的 `command` 区分：

- `backend`：启动 API
- `worker`：启动 Celery worker

这样可以最大限度复用镜像构建结果。

## 8. Nginx 配置草案

### 8.1 目标

Nginx 配置需要同时解决三类问题：

1. 前端静态资源访问
2. `/api` 转发到 backend
3. SPA 路由刷新不报 404

### 8.2 必要配置块

后续 `default.conf` 建议包含以下逻辑块：

- `server`
- `location /`
- `location /api/`
- `try_files`
- 代理头透传

### 8.3 根路径处理

前端静态资源目录应指向构建产物，例如：

- `/usr/share/nginx/html`

根路径访问时直接返回前端页面。

### 8.4 API 转发

`/api/` 应转发到：

- `http://backend:8000`

建议携带：

- `Host`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`

### 8.5 SPA 路由回退

对非静态资源请求使用类似逻辑：

- 先找文件
- 找不到则回退到 `index.html`

这样 `/annotate`、`/annotation-history`、`/admin/overview` 等页面刷新才不会出错。

## 9. 前端发布草案

### 9.1 当前阶段推荐方案

前端先采用“构建产物与 Nginx 解耦”的发布方式：

1. 在发布机执行 `npm run build`
2. 得到 `dist/`
3. 将 `dist/` 挂载给 Nginx

### 9.2 这样做的好处

- 路径简单
- 排查容易
- 不需要先引入多阶段镜像复杂度

### 9.3 后续可升级方向

后续可以进一步收敛成：

- Node 镜像构建
- Nginx 镜像承载静态文件

但第一阶段先不强求。

## 10. 新服务器部署步骤草案

### 10.1 服务器准备

新服务器需要先准备：

- Linux 环境
- Docker
- Docker Compose
- 足够的磁盘空间
- 统一项目目录，例如 `/opt/ttt`

### 10.2 目录准备

建议先创建：

```text
/opt/ttt/uploads
/opt/ttt/artifacts
/opt/ttt/models
/opt/ttt/logs
/opt/ttt/mysql
/opt/ttt/redis
```

### 10.3 代码与配置准备

1. 拉取代码仓库
2. 复制 `.env.example` 为 `.env`
3. 按服务器实际情况填写数据库、Redis、模型路径、上传路径等变量

### 10.4 前端构建准备

1. 安装 Node 依赖
2. 执行前端构建
3. 确认 `dist` 产物位置与 Nginx 挂载路径一致

### 10.5 启动服务

建议执行顺序为：

1. 启动 `mysql` 与 `redis`
2. 确认健康检查通过
3. 启动 `backend`
4. 执行数据库迁移
5. 启动 `worker`
6. 启动 `nginx`

### 10.6 部署后验证

至少验证：

- 前端首页可访问
- 登录成功
- `/api` 请求可达
- 培训页、标注页、复核页可正常打开
- Worker 可以处理至少一类异步任务

## 11. 发布与升级步骤草案

### 11.1 日常更新流程

推荐后续发布流程如下：

1. 备份数据库
2. 拉取最新代码
3. 重新构建 backend 镜像
4. 构建前端产物
5. 执行 Alembic migration
6. 重启 Compose 服务
7. 做冒烟验证

### 11.2 迁移顺序的重要性

数据库迁移建议放在应用服务版本切换之前或之间的明确步骤中，避免：

- 后端代码已更新但数据库结构未更新
- 页面已发布但接口返回结构不兼容

## 12. 换机器部署的便利性判断

### 12.1 达成条件

如果后续部署资产按本文档整理齐全，那么换一台新机器部署时，理论上只需要：

1. 安装 Docker / Docker Compose
2. 拉代码
3. 准备模型目录和持久化目录
4. 修改 `.env`
5. 执行 Compose 启动与迁移

这说明项目将具备较好的可迁移性。

### 12.2 当前仍需补齐的点

要真正做到“拿到另一台机器就方便部署”，仍需继续推进：

- `docker-compose.yml` 正式文件落地
- `.env.example` 正式文件落地
- Dockerfile 正式文件落地
- Nginx 配置正式文件落地
- 本机路径彻底清理
- 部署手册正式版落地

## 13. 当前不建议省略的事项

后续真正实施时，不建议省略以下内容：

- MySQL 数据持久化
- 上传目录持久化
- 模型目录挂载
- Worker 独立服务
- Nginx 路由回退
- Alembic 迁移步骤

这些内容一旦省略，短期也许能“跑起来”，但很容易在多人使用、刷新页面、重启容器或迁移机器时出问题。

## 14. 与正式生产版的衔接关系

本实施草案虽然面向第一版内网多人部署，但它与后续正式生产版并不冲突。

后续向正式生产版扩展时，可以在当前基础上继续叠加：

- HTTPS
- 正式鉴权
- 密码哈希
- 后端权限收口
- 监控与告警
- 数据库备份
- 自动化发布
- 训练节点独立部署

也就是说，当前实施草案是正式生产化的前置基础，而不是一次性方案。

## 15. 总结

从实施角度看，当前项目最适合先落地为：

- `mysql`
- `redis`
- `backend`
- `worker`
- `nginx`

五类核心服务组成的 Docker Compose 服务栈。

只要后续把 Compose 文件、Dockerfile、Nginx 配置、`.env.example` 和部署手册正式补齐，再配合本机路径去耦和部署目录标准化，项目就能较顺畅地实现：

- 同机稳定运行
- 内网多人使用
- 换服务器复现部署

当前仓库已经补入以下部署资产骨架：

1. `deploy/compose/docker-compose.yml`
2. `deploy/compose/.env.example`
3. `deploy/docker/backend/Dockerfile`
4. `deploy/docker/frontend/Dockerfile`
5. `deploy/docker/nginx/default.conf`
6. `deploy/README.md`

下一步建议继续推进：

1. 基于当前草案做一次真实服务器演练
2. 补齐《V7-服务器部署操作手册》
3. 根据演练结果修正路径、迁移顺序和前端构建流程
4. 再进入正式鉴权、安全和监控改造
