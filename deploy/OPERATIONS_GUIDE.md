# 日常运维操作文档

本文记录系统上线后的日常操作：更新代码、重启服务、备份数据、恢复数据和常见问题处理。

## 1. 日常状态检查

进入部署目录：

```bash
cd /opt/ttt/app/deploy/compose
```

查看容器：

```bash
docker compose --env-file .env ps
```

查看后端日志：

```bash
docker compose --env-file .env logs --tail=100 backend
```

跟踪后端日志：

```bash
docker compose --env-file .env logs -f backend
```

查看 Nginx 日志：

```bash
docker compose --env-file .env logs --tail=100 nginx
```

查看资源：

```bash
df -h
free -h
docker system df
du -sh /opt/ttt/*
```

## 2. 更新代码并重新部署

标准流程：

```text
本地修改代码
-> 本地测试
-> git commit
-> git push origin master
-> 服务器 git pull
-> docker compose up -d --build
-> 检查容器和页面
```

服务器执行：

```bash
cd /opt/ttt/app
git status --short
git pull origin master
git log --oneline -3

cd /opt/ttt/app/deploy/compose
docker compose --env-file .env up -d --build
docker compose --env-file .env ps
```

如果只改了文档，不需要重启服务。  
如果改了前端、后端、Dockerfile、依赖、Nginx 配置，都执行 `up -d --build`。

## 3. 数据库迁移

如果代码更新包含新的 Alembic 迁移脚本：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env --profile tools run --rm migrate
docker compose --env-file .env up -d --build
```

注意：

- 已经有正式标注数据后，不要随意清库。
- 首次从完整 SQL 恢复时，通常先导入 SQL，不要先跑迁移，避免“表已存在”。
- 正式运行后如果需要改表结构，应该通过 Alembic 迁移脚本完成。

## 4. 手动备份数据库

正式多人标注后，数据库备份最重要。建议每次大规模标注前后都手动备份一次。

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

检查：

```bash
ls -lh /opt/ttt/backups/
```

部署成功后已验证生成过类似文件：

```text
ttt_prod_after_deploy_YYYY-MM-DD_HHMMSS.sql.gz
```

## 5. 备份上传文件和训练产物

```bash
tar -czf /opt/ttt/backups/ttt_files_$(date +%F_%H%M%S).tar.gz \
  /opt/ttt/uploads \
  /opt/ttt/artifacts
```

模型一般不频繁变化，可单独备份：

```bash
tar -czf /opt/ttt/backups/ttt_models_$(date +%F_%H%M%S).tar.gz /opt/ttt/models
```

## 6. 下载备份到本地

Windows PowerShell：

```powershell
scp root@47.98.118.198:/opt/ttt/backups/ttt_prod_日期.sql.gz C:\Users\29694\Desktop\ttt_db_backup\
scp root@47.98.118.198:/opt/ttt/backups/ttt_files_日期.tar.gz C:\Users\29694\Desktop\ttt_db_backup\
```

也可以用 MobaXterm 左侧 SFTP 文件栏，从 `/opt/ttt/backups` 拖回本地。

原则：

```text
服务器保留最近 14 天备份
重要备份定期下载到本地或对象存储
不要只把唯一备份放在同一台服务器
```

## 7. 设置自动备份

创建脚本：

```bash
mkdir -p /opt/ttt/scripts
nano /opt/ttt/scripts/backup_ttt.sh
```

脚本内容：

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=/opt/ttt/backups
MYSQL_CONTAINER=ttt-mysql
MYSQL_DATABASE=ttt_prod
MYSQL_ROOT_PASSWORD="替换为服务器.env中的MYSQL_ROOT_PASSWORD"

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
chmod +x /opt/ttt/scripts/backup_ttt.sh
```

设置每天凌晨 2 点执行：

```bash
crontab -e
```

加入：

```text
0 2 * * * /opt/ttt/scripts/backup_ttt.sh >> /opt/ttt/backups/backup.log 2>&1
```

检查自动备份日志：

```bash
tail -n 100 /opt/ttt/backups/backup.log
ls -lh /opt/ttt/backups/
```

## 8. 从备份恢复数据库

恢复前建议先停止后端和 worker，避免恢复过程中有写入：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env stop backend worker
```

恢复 `.sql.gz`：

```bash
gunzip -c /opt/ttt/backups/ttt_prod_日期.sql.gz \
  | docker exec -i ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD ttt_prod
```

恢复后启动：

```bash
docker compose --env-file .env up -d
docker compose --env-file .env ps
```

如果要恢复到一台新服务器，流程是：

```text
1. 安装 Docker
2. git clone 仓库
3. 创建 /opt/ttt 运行目录
4. 恢复 /opt/ttt/models
5. 恢复 /opt/ttt/uploads 和 /opt/ttt/artifacts
6. 配置 deploy/compose/.env
7. docker compose up -d --build
8. 导入 .sql.gz
```

## 9. 常见问题处理

### 9.1 Docker Hub 拉镜像超时

现象：

```text
failed to resolve reference docker.io/...
i/o timeout
```

处理：确认 `/etc/docker/daemon.json` 配置了镜像加速，并重启 Docker：

```bash
cat /etc/docker/daemon.json
systemctl restart docker
docker info | grep -A 10 "Registry Mirrors"
```

### 9.2 Debian apt 很慢

后端 Dockerfile 已将 Debian 源替换为阿里云源。如果构建仍访问 `deb.debian.org` 很久，检查：

```bash
grep -n "mirrors.aliyun.com/debian" /opt/ttt/app/deploy/docker/backend/Dockerfile
```

### 9.3 构建时下载 nvidia 包

普通 ECS 是 CPU 服务器，不需要 CUDA 版 PyTorch。若构建时下载：

```text
nvidia-cudnn
nvidia-cublas
nvidia-cuda
```

说明 torch 不是 CPU 版安装。检查 Dockerfile 是否包含：

```text
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 9.4 git pull 提示本地文件会被覆盖

如果服务器上临时改过文件，`git pull` 可能报：

```text
Your local changes would be overwritten by merge
```

先看改了什么：

```bash
cd /opt/ttt/app
git status --short
git diff
```

如果服务器改动已经同步到 GitHub，可以丢弃服务器临时改动：

```bash
git checkout -- 路径/文件名
git pull origin master
```

不要随意 `git reset --hard`，除非确认服务器本地没有需要保留的改动。

### 9.5 页面打不开

检查安全组是否开放 80：

```text
HTTP TCP 80 0.0.0.0/0
```

服务器检查：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env ps
curl -I http://127.0.0.1
docker compose --env-file .env logs --tail=100 nginx
```

### 9.6 登录或接口异常

查看后端日志：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env logs --tail=200 backend
```

检查数据库：

```bash
docker exec -it ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD -e "USE ttt_prod; SELECT COUNT(*) FROM users; SELECT COUNT(*) FROM questions;"
```

### 9.7 磁盘不足

检查：

```bash
df -h
docker system df
du -sh /opt/ttt/*
```

可清理旧构建缓存：

```bash
docker builder prune -f
```

谨慎清理未使用镜像：

```bash
docker image prune -f
```

不要删除：

```text
/opt/ttt/mysql
/opt/ttt/uploads
/opt/ttt/artifacts
/opt/ttt/models
/opt/ttt/backups 中仍需保留的备份
```

## 10. 重要原则

```text
代码：GitHub 管理
配置：服务器 .env 管理，不进 GitHub
数据库：MySQL 管理，定期 mysqldump 备份
上传文件/训练产物：/opt/ttt/uploads 和 /opt/ttt/artifacts 管理
模型：/opt/ttt/models 管理
公网入口：只开放 80/443/22
```

