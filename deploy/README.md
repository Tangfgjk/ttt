# Deploy Assets

`deploy/` 存放 Docker Compose 部署和运维相关文件。

## 目录说明

- `compose/docker-compose.yml`：主 Compose 编排文件，适用于 CPU 部署。
- `compose/docker-compose.cuda.yml`：CUDA 服务器覆盖配置，需要和主 Compose 文件一起使用。
- `compose/.env.example`：部署变量模板，实际部署时复制为 `.env`。
- `docker/backend/Dockerfile`：后端、worker、迁移任务共用镜像。
- `docker/frontend/Dockerfile`：前端构建和 Nginx 运行镜像。
- `docker/nginx/default.conf`：前端静态文件托管和 API 反向代理配置。

## 推荐阅读顺序

1. `NEW_SERVER_CUDA_DEPLOYMENT.md`
   - 给新接手部署的人使用，覆盖从购买新服务器、拉取 GitHub 代码、上传模型和数据库，到 CUDA 训练验证的完整流程。
2. `DEPLOYMENT_GUIDE.md`
   - 早期从零部署流程记录。
3. `OPERATIONS_GUIDE.md`
   - 日常更新代码、重新部署、备份、恢复和排错命令。
4. `DEPLOYMENT_RUNBOOK.md`
   - 首次部署过程中的补充记录。

## 常用命令

CPU 部署：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env up -d --build
docker compose --env-file .env ps
```

CUDA 部署：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml up -d --build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml ps
```

数据库备份：

```bash
cd /opt/ttt/app/deploy/compose
set -a
source .env
set +a
mkdir -p /opt/ttt/backups
docker exec ${COMPOSE_PROJECT_NAME:-ttt}-mysql mysqldump \
  -uroot -p"$MYSQL_ROOT_PASSWORD" \
  --default-character-set=utf8mb4 \
  --single-transaction --routines --triggers --events \
  "$MYSQL_DATABASE" \
  | gzip > /opt/ttt/backups/ttt_prod_$(date +%F_%H%M%S).sql.gz
```
