# FIN 云端纯标注部署交接文档

本文是当前推荐且唯一需要交给部署人员执行的云服务器部署流程。

云服务器只承担：

- 网站访问与 API 服务
- 标注员培训准入
- 题目领取、标注、复核和管理员治理
- MySQL 正式数据库与上传文件存储
- 数据备份

以下功能只在本地电脑运行：

- 模型训练
- CoreSet 选题
- 低置信度预测选题

云服务器不需要 GPU、CUDA、PyTorch、Transformers、模型目录、Redis 或 Celery worker。

## 1. 部署前准备

### 1.1 服务器建议

- 操作系统：Ubuntu 22.04 或 24.04 64 位
- CPU：4 核
- 内存：8 GiB
- 系统盘：至少 80 GiB，建议 100 GiB
- 公网带宽：5 Mbps 以上
- GPU：不需要

安全组入方向只开放：

- TCP 22：SSH，建议仅允许管理员公网 IP
- TCP 80：HTTP
- TCP 443：配置 HTTPS 后使用

不要开放 MySQL 3306、后端 8000 或其他内部端口。

### 1.2 代码来源

GitHub 仓库是公开仓库，服务器直接执行：

```bash
git clone https://github.com/Tangfgjk/ttt.git app
```

服务器只拉取代码，不需要向 GitHub 推送。

### 1.3 需要单独上传的文件

本地目录：

```text
C:\Users\29694\Desktop\单独上传文件
```

必须上传：

1. `db_backups` 中最新的完整数据库 SQL 或 `.sql.gz`
2. `uploads` 目录

不需要上传：

- `math_mlm_model`
- `artifacts`
- `checkpoint-*`
- CUDA 安装包

## 2. 登录并初始化服务器

```bash
ssh root@服务器公网IP
```

创建目录：

```bash
mkdir -p /opt/ttt/{backups,uploads,mysql}
cd /opt/ttt
```

安装基础工具：

```bash
apt update
apt install -y ca-certificates curl git vim unzip
```

## 3. 安装 Docker Compose

已经安装 Docker 的服务器可跳过安装，只执行最后两条版本检查命令。

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

docker --version
docker compose version
```

如果 Docker Hub 下载超时，可配置镜像源：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
```

## 4. 拉取代码

```bash
cd /opt/ttt
git clone https://github.com/Tangfgjk/ttt.git app
cd /opt/ttt/app
git log --oneline -3
```

以后不要删除 `/opt/ttt/app/deploy/compose/.env`。

## 5. 上传数据库和 uploads

以下命令在本地 Windows PowerShell 执行，把 IP 和文件名换成实际值：

```powershell
$server = "服务器公网IP"
$source = "C:\Users\29694\Desktop\单独上传文件"

scp "$source\db_backups\最新数据库备份.sql" root@${server}:/opt/ttt/backups/
scp -r "$source\uploads" root@${server}:/opt/ttt/
```

如果数据库是 `.sql.gz`，直接上传压缩文件，不要先用压缩软件解压。

在服务器检查：

```bash
ls -lh /opt/ttt/backups
du -sh /opt/ttt/uploads
```

## 6. 配置环境变量

```bash
cd /opt/ttt/app/deploy/compose
cp .env.example .env
vim .env
```

至少修改以下内容：

```dotenv
COMPOSE_PROJECT_NAME=ttt
NGINX_HTTP_PORT=80

HOST_UPLOADS_DIR=/opt/ttt/uploads
HOST_ARTIFACTS_DIR=/opt/ttt/artifacts
HOST_MODELS_DIR=/opt/ttt/models
HOST_MYSQL_DIR=/opt/ttt/mysql

MYSQL_DATABASE=ttt_prod
MYSQL_USER=ttt_user
MYSQL_PASSWORD=请设置独立强密码
MYSQL_ROOT_PASSWORD=请设置另一个独立强密码
DATABASE_URL=mysql+pymysql://ttt_user:与MYSQL_PASSWORD相同@mysql:3306/ttt_prod

APP_ENV=prod
APP_DEBUG=false
ENABLE_DOCS=false

INSTALL_ML=false
```

注意：

- 密码中如包含 `@`、`:`、`/`、`#` 等 URL 特殊字符，需要进行 URL 编码。
- `INSTALL_ML=false` 是纯标注镜像的关键设置。
- 模型和 artifacts 路径可以保留为空目录，无需上传任何内容。

限制 `.env` 权限：

```bash
chmod 600 .env
```

## 7. 验证 Compose 配置

以后所有云端部署命令都同时使用两个 Compose 文件：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  config > /tmp/ttt-compose-config.yml
```

确认没有报错后再启动。

## 8. 首次启动 MySQL并导入数据库

先只启动 MySQL：

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  up -d mysql
```

检查健康状态：

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  ps
```

导入未压缩 SQL：

```bash
set -a
source .env
set +a

docker exec -i ${COMPOSE_PROJECT_NAME:-ttt}-mysql \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" \
  < /opt/ttt/backups/最新数据库备份.sql
```

导入 `.sql.gz`：

```bash
gzip -dc /opt/ttt/backups/最新数据库备份.sql.gz \
  | docker exec -i ${COMPOSE_PROJECT_NAME:-ttt}-mysql \
      mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"
```

导入完成后检查：

```bash
docker exec -it ${COMPOSE_PROJECT_NAME:-ttt}-mysql \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e \
  "USE $MYSQL_DATABASE; SHOW TABLES; SELECT COUNT(*) AS users FROM users; SELECT COUNT(*) AS questions FROM questions;"
```

## 9. 执行迁移并启动网站

执行数据库迁移：

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  --profile tools run --rm migrate
```

构建并启动：

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  up -d --build
```

查看状态：

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  ps
```

正常应看到：

- `ttt-mysql`：healthy
- `ttt-backend`：healthy
- `ttt-nginx`：running

不会出现 Redis 或 worker 容器，这是预期结果。

## 10. 健康检查和功能检查

```bash
curl http://127.0.0.1/api/v1/system/health
curl http://127.0.0.1/api/v1/system/capabilities
```

能力接口预期包含：

```json
{
  "ml_runtime_available": false,
  "missing_packages": ["torch", "transformers"]
}
```

浏览器访问：

```text
http://服务器公网IP/
```

依次检查：

1. 管理员可以登录。
2. 标注员可以培训准入、领取和提交题目。
3. 复核员可以领取并提交复核。
4. 管理员可以查看和回收任务。
5. 点击模型训练、CoreSet 或低置信度预测时，页面提示当前服务器没有机器学习环境。

## 11. 更新代码和重新部署

更新前先备份数据库：

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
  | gzip > /opt/ttt/backups/ttt_prod_before_update_$(date +%F_%H%M%S).sql.gz
```

拉取并部署：

```bash
cd /opt/ttt/app
git status --short
git pull --ff-only origin master

cd deploy/compose
docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  --profile tools run --rm migrate

docker compose --env-file .env \
  -f docker-compose.yml \
  -f docker-compose.annotation.yml \
  up -d --build
```

最后执行 `ps` 和两个 `curl` 健康检查。

## 12. 定期备份

### 12.1 数据库备份

建议每天一次，至少每周一次：

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

gzip -t /opt/ttt/backups/ttt_prod_*.sql.gz
ls -lh /opt/ttt/backups
```

### 12.2 uploads 备份

```bash
tar -czf /opt/ttt/backups/uploads_$(date +%F_%H%M%S).tar.gz \
  -C /opt/ttt uploads
```

### 12.3 下载到本地用于训练

在本地 PowerShell 执行：

```powershell
scp root@服务器公网IP:/opt/ttt/backups/备份文件.sql.gz C:\Users\29694\Desktop\ttt\db_backups\
```

下载后先运行 gzip 完整性检查，再恢复到本地 MySQL。模型训练、CoreSet 和低置信度预测都基于本地同步后的数据库执行。

## 13. 常用排错命令

```bash
cd /opt/ttt/app/deploy/compose

docker compose --env-file .env -f docker-compose.yml -f docker-compose.annotation.yml ps
docker compose --env-file .env -f docker-compose.yml -f docker-compose.annotation.yml logs --tail=200 backend
docker compose --env-file .env -f docker-compose.yml -f docker-compose.annotation.yml logs --tail=200 nginx
docker compose --env-file .env -f docker-compose.yml -f docker-compose.annotation.yml logs --tail=200 mysql

df -h
docker system df
free -h
```

如果磁盘不足，只清理未使用的构建缓存和镜像：

```bash
docker builder prune -f
docker image prune -f
```

不要删除 `/opt/ttt/mysql`、`/opt/ttt/uploads` 或 `/opt/ttt/backups`。

## 14. 关于 Redis

当前代码中的 Redis 配置只连接 Celery。仓库目前没有注册任何 Celery task，主动学习任务使用后端直接启动独立 Python 进程，不经过 Celery。

因此：

- 标注、复核、培训准入和登录不使用 Redis。
- 云端纯标注部署不启动 Redis 或 Celery worker。
- 删除 Redis 容器不会影响正式标注数据，正式数据保存在 MySQL 和 uploads 中。

## 15. 最终检查清单

- [ ] GitHub 代码已克隆到 `/opt/ttt/app`
- [ ] 最新数据库已上传并导入
- [ ] uploads 已上传到 `/opt/ttt/uploads`
- [ ] `.env` 中数据库密码已经修改
- [ ] `.env` 中 `INSTALL_ML=false`
- [ ] 安全组没有开放 3306 和 8000
- [ ] MySQL、backend、Nginx 正常运行
- [ ] health 返回正常
- [ ] capabilities 显示 ML 不可用
- [ ] 标注、复核、培训准入均可正常使用
- [ ] 三个本地 ML 功能在云端点击时显示明确提示
- [ ] 数据库和 uploads 已建立定期备份流程
