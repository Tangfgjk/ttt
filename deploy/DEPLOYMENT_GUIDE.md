# 云服务器部署操作文档

本文记录从零开始在阿里云 ECS 上部署 K12 学科标注平台的完整流程。当前生产式试运行入口为：

```text
http://47.98.118.198
```

服务器实际运行目录统一使用 `/opt/ttt`。本文不记录任何真实密码，真实密码只保存在服务器 `/opt/ttt/app/deploy/compose/.env` 中。

## 1. 部署架构

```text
浏览器
  -> Nginx 容器: 80
      -> 前端静态文件
      -> /api/ 反向代理到 backend:8000
  -> FastAPI backend 容器
  -> MySQL 容器
  -> Redis 容器
  -> Celery worker 容器
```

Docker Compose 管理的服务：

```text
mysql    数据库
redis    缓存和任务队列
backend  FastAPI 接口
worker   Celery 后台任务
nginx    前端静态文件和 API 反向代理
migrate  Alembic 数据库迁移工具
```

## 2. 阿里云 ECS 初始化

推荐配置：

```text
系统：Ubuntu 22.04 64 位
配置：4 核 8G 起步
磁盘：40G 可试用，长期建议 100G 或 200G
公网：开启
```

安全组入方向保留：

```text
SSH    TCP 22   0.0.0.0/0
HTTP   TCP 80   0.0.0.0/0
HTTPS  TCP 443  0.0.0.0/0
ICMP   ping，可选
```

不要开放：

```text
MySQL 3306
Redis 6379
Backend 8000
RDP 3389
```

`3389` 是 Windows 远程桌面端口，Ubuntu 不需要，已删除。

## 3. 安装基础工具和 Docker

登录服务器：

```bash
ssh root@47.98.118.198
```

安装基础工具：

```bash
apt update
apt install -y ca-certificates curl git vim unzip
```

使用阿里云 Docker CE 源安装 Docker：

```bash
rm -f /etc/apt/sources.list.d/docker.list
rm -f /etc/apt/keyrings/docker.asc

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/ubuntu jammy stable" > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

docker --version
docker compose version
```

配置 Docker 镜像加速：

```bash
mkdir -p /etc/docker

cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
docker info | grep -A 10 "Registry Mirrors"
```

## 4. 配置 GitHub Deploy Key

因为仓库是 private，推荐服务器使用 SSH Deploy Key 拉代码，不使用个人密码或暴露 token。

服务器生成 SSH key：

```bash
mkdir -p ~/.ssh
ssh-keygen -t ed25519 -C "aliyun-ecs-ttt" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

复制输出中 `ssh-ed25519 ... aliyun-ecs-ttt` 这一整行，添加到 GitHub：

```text
仓库 ttt -> Settings -> Deploy keys -> Add deploy key
Title: aliyun-ecs-ttt
Key: 粘贴 ssh-ed25519 公钥
Allow write access: 不勾选
```

服务器配置 GitHub 走 SSH 443 端口：

```bash
cat > ~/.ssh/config <<'EOF'
Host github.com
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/id_ed25519
EOF

chmod 600 ~/.ssh/config
ssh -T git@github.com
```

出现下面文字即认证成功：

```text
You've successfully authenticated, but GitHub does not provide shell access.
```

## 5. 拉取代码和创建目录

```bash
mkdir -p /opt/ttt
cd /opt/ttt
git clone git@github.com:Tangfgjk/ttt.git app
```

创建运行数据目录：

```bash
mkdir -p /opt/ttt/uploads \
  /opt/ttt/artifacts \
  /opt/ttt/models \
  /opt/ttt/mysql \
  /opt/ttt/redis \
  /opt/ttt/backups
```

目录约定：

```text
/opt/ttt/app        GitHub 代码
/opt/ttt/uploads    上传文件和导入文件
/opt/ttt/artifacts  训练和主动学习产物
/opt/ttt/models     模型文件
/opt/ttt/mysql      MySQL 持久化数据
/opt/ttt/redis      Redis 持久化数据
/opt/ttt/backups    数据库和文件备份
```

## 6. 配置 .env

```bash
cd /opt/ttt/app/deploy/compose
cp .env.example .env
nano .env
```

至少修改：

```text
MYSQL_DATABASE=ttt_prod
MYSQL_USER=ttt_user
MYSQL_PASSWORD=替换为实际密码
MYSQL_ROOT_PASSWORD=替换为实际密码
DATABASE_URL=mysql+pymysql://ttt_user:同一个MYSQL_PASSWORD@mysql:3306/ttt_prod

HOST_UPLOADS_DIR=/opt/ttt/uploads
HOST_ARTIFACTS_DIR=/opt/ttt/artifacts
HOST_MODELS_DIR=/opt/ttt/models
HOST_MYSQL_DIR=/opt/ttt/mysql
HOST_REDIS_DIR=/opt/ttt/redis

EMBEDDING_MODEL_PATH=/data/models/math_mlm_model
ACTIVE_LEARNING_CHECKPOINT_DIR=/data/artifacts/active_learning
```

`.env` 不提交 GitHub。

## 7. 上传数据库和模型

数据库 SQL 上传到：

```text
/opt/ttt/backups/competency_annotation_dev_20260527.sql
```

模型目录上传到：

```text
/opt/ttt/models/math_mlm_model
```

模型目录最终应包含：

```text
added_tokens.json
config.json
model.safetensors
special_tokens_map.json
tokenizer.json
tokenizer_config.json
training_args.bin
vocab.txt
```

不需要上传：

```text
checkpoint-9500/
checkpoint-9960/
```

检查：

```bash
ls -lh /opt/ttt/backups/
ls -lh /opt/ttt/models/math_mlm_model
```

## 8. 启动服务

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env up -d --build
docker compose --env-file .env ps
```

正常状态应包含：

```text
ttt-mysql    healthy
ttt-redis    healthy
ttt-backend  healthy
ttt-worker   started
ttt-nginx    started
```

首次构建说明：

- 前端由 `deploy/docker/frontend/Dockerfile` 自动构建，不需要服务器手动安装 Node。
- 后端 Dockerfile 已使用阿里云 Debian/PyPI 源，并安装 CPU 版 torch。
- 如果看到大量 `nvidia-*` 包下载，说明 Dockerfile 没有使用 CPU 版 torch，需要检查 `deploy/docker/backend/Dockerfile`。

## 9. 导入数据库

导入完整 SQL：

```bash
docker exec -i ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD ttt_prod \
  < /opt/ttt/backups/competency_annotation_dev_20260527.sql
```

导入完成通常没有额外输出。检查表和数据量：

```bash
docker exec -it ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD -e "USE ttt_prod; SHOW TABLES;"
docker exec -it ttt-mysql mysql -uroot -p你的MYSQL_ROOT_PASSWORD -e "USE ttt_prod; SELECT COUNT(*) AS users_count FROM users; SELECT COUNT(*) AS questions_count FROM questions;"
```

当前部署验证过：

```text
users_count = 7
questions_count = 42990
```

## 10. 验证访问

浏览器访问：

```text
http://47.98.118.198
```

服务检查：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env logs --tail=100 backend
curl -I http://127.0.0.1
```

看到 `/api/v1/system/health 200 OK`、页面可打开、登录正常，即部署成功。

