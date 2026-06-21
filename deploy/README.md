# Deploy Assets

`deploy/` 存放 Docker Compose 部署和运维相关文件。

## 目录说明

- `compose/docker-compose.yml`：主 Compose 编排文件。
- `compose/docker-compose.annotation.yml`：云端纯标注覆盖配置，跳过 PyTorch 和 Transformers 安装。
- `compose/docker-compose.cuda.yml`：历史 CUDA 覆盖配置，仅供本地或专用训练服务器参考。
- `compose/.env.example`：部署变量模板，实际部署时复制为 `.env`。
- `docker/backend/Dockerfile`：后端和迁移任务共用镜像，可通过 `INSTALL_ML` 控制机器学习依赖。
- `docker/frontend/Dockerfile`：前端构建和 Nginx 运行镜像。
- `docker/nginx/default.conf`：前端静态文件托管和 API 反向代理配置。

## 推荐阅读顺序

1. `FIN_DEPLOYMENT_GUIDE.md`
   - 当前最终交付版。服务器直接 HTTPS 克隆代码，只上传数据库和 uploads，按纯标注模式部署。
2. `NEW_SERVER_CUDA_DEPLOYMENT.md`
   - 历史 CUDA 部署参考，不是当前云端部署方案。
3. `DEPLOYMENT_GUIDE.md`
   - 早期从零部署流程记录。
4. `OPERATIONS_GUIDE.md`
   - 日常更新代码、重新部署、备份、恢复和排错命令。
5. `DEPLOYMENT_RUNBOOK.md`
   - 首次部署过程中的补充记录。

## 常用命令

FIN 云端纯标注部署：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.annotation.yml up -d --build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.annotation.yml ps
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
