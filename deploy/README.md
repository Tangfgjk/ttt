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
  - 可选的前端多阶段构建镜像定义
- `docker/nginx/default.conf`
  - Nginx 静态托管与 API 反代配置

## 使用建议

1. 将 `compose/.env.example` 复制为 `compose/.env`
2. 按服务器实际路径修改宿主机挂载目录和密码
3. 先构建前端 `dist`，并将其同步到 `HOST_FRONTEND_DIST_DIR`
4. 使用 `docker compose --env-file .env up -d` 启动服务
5. 首次部署前执行一次迁移：

```bash
docker compose --env-file .env --profile tools run --rm migrate
```
