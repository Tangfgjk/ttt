# 部署与运维记录

本文记录 K12 学科标注平台上云部署、代码更新、数据迁移和定期备份的约定。服务器运行时请优先参考本文。

## 1. 部署目标

当前部署目标是让多人通过公网访问同一套标注系统：

- 代码从 GitHub 仓库拉取。
- 前端构建为静态文件，由 Nginx 提供访问。
- 后端 FastAPI、MySQL、Redis、Celery worker 由 Docker Compose 管理。
- 正式标注数据写入云服务器 MySQL。
- 本地电脑只作为开发环境和备份保存环境，不作为正式数据库。

推荐服务器配置：

- Ubuntu 22.04 或 24.04。
- 4 核 8G 起步，长期多人使用推荐 8 核 16G。
- 系统盘 40G 可以用于免费试用，长期推荐 100G 或 200G。
- 安全组开放 22、80，配置 HTTPS 后开放 443。
- 不对公网开放 3306、6379、8000。

## 2. 代码与运行数据边界

GitHub 只保存代码和部署模板，不保存运行数据。

应该提交到 GitHub：

- `backend/`
- `frontend/`
- `deploy/`
- `docs/`
- 数据库迁移脚本，例如 `backend/alembic/versions/*.py`

不应该提交到 GitHub：

- `MLM/`
- `uploads/`
- `db_backups/`
- `backend/.env`
- `deploy/compose/.env`
- `frontend/dist/`
- `backend/artifacts/`
- MySQL、Redis 的数据目录

一句话原则：

```text
GitHub 管代码，MySQL 管标注数据，uploads/artifacts 管运行文件和结果。
```

## 3. 服务器目录规划

建议统一使用 `/opt/ttt`：

```text
/opt/ttt/app              GitHub 仓库代码
/opt/ttt/uploads          上传文件、导入文件
/opt/ttt/artifacts        训练产物、主动学习结果
/opt/ttt/models           模型文件
/opt/ttt/mysql            MySQL 持久化数据
/opt/ttt/redis            Redis 持久化数据
/opt/ttt/frontend-dist    前端构建产物
/opt/ttt/backups          数据库和文件备份
```

首次创建目录：

```bash
sudo mkdir -p /opt/ttt/app \
  /opt/ttt/uploads \
  /opt/ttt/artifacts \
  /opt/ttt/models \
  /opt/ttt/mysql \
  /opt/ttt/redis \
  /opt/ttt/frontend-dist \
  /opt/ttt/backups
```

## 4. 首次部署流程

### 4.1 拉取代码

如果服务器已配置 GitHub SSH key：

```bash
cd /opt/ttt
git clone git@github.com:Tangfgjk/ttt.git app
```

如果暂时使用 HTTPS：

```bash
cd /opt/ttt
git clone https://github.com/Tangfgjk/ttt.git app
```

仓库是 private 时，HTTPS/SSH 都需要授权。

### 4.2 上传模型

本地只需要上传实际运行需要的模型目录：

```text
C:\Users\29694\Desktop\ttt\MLM\rePretrain.zip\rePretrain\math_mlm_model
```

服务器目标路径：

```text
/opt/ttt/models/math_mlm_model
```

不要把整个 `MLM/`、训练 checkpoint、重复压缩包都传到服务器，避免占满系统盘。

### 4.3 上传本地数据库导出

当前已生成的本地数据库导出文件：

```text
C:\Users\29694\Desktop\ttt\db_backups\competency_annotation_dev_20260527.sql
```

上传到服务器：

```text
/opt/ttt/backups/competency_annotation_dev_20260527.sql
```

该 SQL 文件包含表结构和数据，不要公开，不要提交到 GitHub。

### 4.4 配置环境变量

```bash
cd /opt/ttt/app/deploy/compose
cp .env.example .env
```

重点修改：

```text
MYSQL_DATABASE=ttt_prod
MYSQL_USER=ttt_user
MYSQL_PASSWORD=替换为强密码
MYSQL_ROOT_PASSWORD=替换为强密码

DATABASE_URL=mysql+pymysql://ttt_user:同一个MYSQL_PASSWORD@mysql:3306/ttt_prod

HOST_UPLOADS_DIR=/opt/ttt/uploads
HOST_ARTIFACTS_DIR=/opt/ttt/artifacts
HOST_MODELS_DIR=/opt/ttt/models
HOST_MYSQL_DIR=/opt/ttt/mysql
HOST_REDIS_DIR=/opt/ttt/redis
HOST_FRONTEND_DIST_DIR=/opt/ttt/frontend-dist

EMBEDDING_MODEL_PATH=/data/models/math_mlm_model
ACTIVE_LEARNING_CHECKPOINT_DIR=/data/artifacts/active_learning
```

`deploy/compose/.env` 是服务器私有配置，不提交 GitHub。

### 4.5 构建前端

```bash
cd /opt/ttt/app/frontend
npm ci
npm run build
rm -rf /opt/ttt/frontend-dist/*
cp -r dist/* /opt/ttt/frontend-dist/
```

### 4.6 启动服务

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env up -d --build
```

查看服务：

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs -f backend
```

### 4.7 导入本地数据库

如果数据库不存在，先创建：

```bash
docker exec -it ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD \
  -e "CREATE DATABASE IF NOT EXISTS ttt_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

导入本地 SQL：

```bash
docker exec -i ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD ttt_prod \
  < /opt/ttt/backups/competency_annotation_dev_20260527.sql
```

如果导入时报“表已存在”，说明服务器数据库已经被迁移脚本创建过。处理方式二选一：

- 首次全量迁移时，可以清空服务器新库后重新导入完整 SQL。
- 如果服务器已经有正式标注数据，不要清库，应改为按表或按数据导入。

首次部署建议先导入完整 SQL，再运行系统检查页面、用户、题库、标注记录是否正常。

## 5. 后续代码更新

本地修改代码不会自动同步到服务器。推荐流程：

```text
本地开发
-> git commit
-> git push origin master
-> 服务器 git pull
-> 重新构建并重启服务
```

服务器更新代码：

```bash
cd /opt/ttt/app
git pull origin master
```

如果前端有修改：

```bash
cd /opt/ttt/app/frontend
npm ci
npm run build
rm -rf /opt/ttt/frontend-dist/*
cp -r dist/* /opt/ttt/frontend-dist/
```

如果后端、Dockerfile 或依赖有修改：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env up -d --build
```

如果新增或修改了数据库迁移脚本：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env --profile tools run --rm migrate
docker compose --env-file .env up -d --build
```

不要长期直接在服务器上手改代码。服务器只负责运行，代码以 GitHub 为准。

## 6. 定期备份

正式多人标注后，备份比代码更重要。至少备份：

- MySQL 数据库导出的 `.sql.gz`
- `/opt/ttt/uploads`
- `/opt/ttt/artifacts`
- 必要时备份 `/opt/ttt/models`
- 服务器 `deploy/compose/.env` 另存一份到安全位置

### 6.1 手动备份数据库

```bash
mkdir -p /opt/ttt/backups

docker exec ttt-mysql mysqldump \
  -uroot \
  -p你的MYSQL_ROOT_PASSWORD \
  --default-character-set=utf8mb4 \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  ttt_prod \
  | gzip > /opt/ttt/backups/ttt_prod_$(date +%F_%H%M%S).sql.gz
```

### 6.2 手动打包运行文件

```bash
tar -czf /opt/ttt/backups/ttt_files_$(date +%F_%H%M%S).tar.gz \
  /opt/ttt/uploads \
  /opt/ttt/artifacts
```

模型目录较大，且通常不频繁变化。模型首次上传后可以单独备份一次：

```bash
tar -czf /opt/ttt/backups/ttt_models_$(date +%F_%H%M%S).tar.gz /opt/ttt/models
```

### 6.3 下载备份到本地电脑

Windows PowerShell 示例：

```powershell
scp root@服务器公网IP:/opt/ttt/backups/ttt_prod_日期.sql.gz C:\Users\29694\Desktop\ttt_db_backup\
scp root@服务器公网IP:/opt/ttt/backups/ttt_files_日期.tar.gz C:\Users\29694\Desktop\ttt_db_backup\
```

也可以使用 WinSCP、Xftp、FileZilla 下载。

### 6.4 建议的自动备份策略

建议每天凌晨备份一次数据库，保留最近 14 天：

```bash
sudo mkdir -p /opt/ttt/scripts
sudo nano /opt/ttt/scripts/backup_ttt.sh
```

脚本内容示例：

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=/opt/ttt/backups
MYSQL_CONTAINER=ttt-mysql
MYSQL_DATABASE=ttt_prod
MYSQL_ROOT_PASSWORD="替换为MYSQL_ROOT_PASSWORD"

mkdir -p "$BACKUP_DIR"

docker exec "$MYSQL_CONTAINER" mysqldump \
  -uroot \
  -p"$MYSQL_ROOT_PASSWORD" \
  --default-character-set=utf8mb4 \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  "$MYSQL_DATABASE" \
  | gzip > "$BACKUP_DIR/${MYSQL_DATABASE}_$(date +%F_%H%M%S).sql.gz"

tar -czf "$BACKUP_DIR/ttt_files_$(date +%F_%H%M%S).tar.gz" \
  /opt/ttt/uploads \
  /opt/ttt/artifacts

find "$BACKUP_DIR" -name "*.sql.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "ttt_files_*.tar.gz" -mtime +14 -delete
```

授权：

```bash
sudo chmod +x /opt/ttt/scripts/backup_ttt.sh
```

配置 crontab：

```bash
sudo crontab -e
```

每天凌晨 2 点执行：

```text
0 2 * * * /opt/ttt/scripts/backup_ttt.sh >> /opt/ttt/backups/backup.log 2>&1
```

自动备份仍建议定期下载到本地或对象存储。只放在同一台服务器上，服务器到期或磁盘损坏时仍可能丢失。

## 7. 服务器到期或迁移

到期前必须下载：

```text
/opt/ttt/backups/*.sql.gz
/opt/ttt/backups/ttt_files_*.tar.gz
/opt/ttt/models 或模型备份包
/opt/ttt/app/deploy/compose/.env
```

新服务器恢复流程：

1. 从 GitHub 拉取代码。
2. 安装 Docker 和 Docker Compose。
3. 创建 `/opt/ttt` 运行目录。
4. 恢复模型到 `/opt/ttt/models`。
5. 恢复 uploads/artifacts。
6. 创建并配置 `deploy/compose/.env`。
7. 启动 Docker Compose。
8. 将 `.sql.gz` 导入 MySQL。

导入 `.sql.gz` 示例：

```bash
gunzip -c /opt/ttt/backups/ttt_prod_日期.sql.gz \
  | docker exec -i ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD ttt_prod
```

## 8. 常用排查命令

查看容器：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env ps
```

查看后端日志：

```bash
docker compose --env-file .env logs -f backend
```

查看 Nginx 日志：

```bash
docker compose --env-file .env logs -f nginx
```

查看 MySQL 是否健康：

```bash
docker exec -it ttt-mysql mysqladmin ping -uroot -p你的MYSQL_ROOT_PASSWORD
```

检查磁盘空间：

```bash
df -h
du -sh /opt/ttt/*
```

检查公网端口：

```bash
ss -tlnp
```

