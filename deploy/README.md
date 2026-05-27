# Deploy Assets

该目录用于存放 Docker Compose 部署资产。

## 目录说明

- `compose/docker-compose.yml`
  - 本地/服务器 Docker Compose 编排文件
- `compose/.env.example`
  - 部署变量模板
- `docker/backend/Dockerfile`
  - backend 与 worker 共用镜像定义
- `docker/frontend/Dockerfile`
  - 前端多阶段构建与 Nginx 运行镜像定义
- `docker/nginx/default.conf`
  - Nginx 静态托管与 API 反代配置

## 使用建议

1. 将 `compose/.env.example` 复制为 `compose/.env`
2. 按服务器实际路径修改宿主机挂载目录和密码
3. 使用 `docker compose --env-file .env up -d --build` 构建并启动服务
4. 首次部署如果使用空数据库，可执行一次迁移：

```bash
docker compose --env-file .env --profile tools run --rm migrate
```

如果首次部署要导入本地完整 SQL 备份，通常先启动 MySQL，再导入 SQL；不要在导入完整结构前先迁移以免出现“表已存在”。更多细节见 `DEPLOYMENT_RUNBOOK.md`。
