# FIN 部署交接文档

本文档给实际部署人员使用。按照本文档操作，可以在新服务器上从 GitHub 拉取代码，并把本地准备好的数据、模型和附件上传到服务器，最终启动 K12 学科标注平台。

## 0. 本次交付内容

### 0.1 GitHub 代码

代码仓库：

```text
https://github.com/Tangfgjk/ttt.git
```

部署分支：

```text
master
```

服务器上代码目录统一使用：

```text
/opt/ttt/app
```

说明：

- 当前 GitHub 仓库已经设置为 public，新服务器不需要配置 GitHub SSH key，也不需要 GitHub token。
- 服务器只需要从 GitHub 拉取代码，不需要向 GitHub 上传或推送任何内容。

### 0.2 需要单独上传的文件

这些文件不在 GitHub 仓库里，需要从本地电脑单独上传。

本地交付文件夹：

```text
C:\Users\29694\Desktop\单独上传文件
```

当前该文件夹包含：

```text
单独上传文件
├─ artifacts
├─ db_backups
│  └─ local_competency_annotation_dev_2026-06-18_190531.sql
├─ math_mlm_model
│  ├─ added_tokens.json
│  ├─ config.json
│  ├─ model.safetensors
│  ├─ special_tokens_map.json
│  ├─ tokenizer.json
│  ├─ tokenizer_config.json
│  ├─ training_args.bin
│  └─ vocab.txt
└─ uploads
```

上传到服务器后的对应关系：

| 本地路径 | 服务器路径 | 作用 |
| --- | --- | --- |
| `C:\Users\29694\Desktop\单独上传文件\db_backups\local_competency_annotation_dev_2026-06-18_190531.sql` | `/opt/ttt/backups/local_competency_annotation_dev_2026-06-18_190531.sql` | 数据库完整备份 |
| `C:\Users\29694\Desktop\单独上传文件\math_mlm_model` | `/opt/ttt/models/math_mlm_model` | 嵌入模型 |
| `C:\Users\29694\Desktop\单独上传文件\uploads` | `/opt/ttt/uploads` | 导入文件、附件、题目相关上传文件 |
| `C:\Users\29694\Desktop\单独上传文件\artifacts` | `/opt/ttt/artifacts` | 主动学习、训练模型、历史训练产物 |

不要上传：

- `.git`
- `node_modules`
- `.venv`
- `__pycache__`
- 本地日志文件

## 1. 服务器要求

推荐系统：

```text
Ubuntu 22.04 LTS
```

本次交付要求服务器必须支持 CUDA，因为后续需要在服务器上训练模型。建议配置：

```text
NVIDIA GPU / 8 GB 以上显存 / 80 GB 以上磁盘，推荐 120 GB
```

CPU-only 服务器不作为本次交付目标。

安全组只开放：

| 端口 | 用途 | 建议 |
| --- | --- | --- |
| `22` | SSH 登录 | 只对管理员公网 IP 开放 |
| `80` | Web 访问 | 对用户开放 |
| `443` | HTTPS | 配置 HTTPS 后再开放 |

不要开放：

| 端口 | 原因 |
| --- | --- |
| `3306` | MySQL 不直接暴露公网 |
| `6379` | Redis 不直接暴露公网 |
| `3389` | Linux 服务器不需要 RDP |

## 2. 登录服务器

在 Windows PowerShell、MobaXterm 或其他 SSH 工具中登录：

```bash
ssh root@服务器公网IP
```

以下命令都在服务器终端执行，除非特别说明是在 Windows PowerShell 执行。

## 3. 初始化服务器目录

```bash
apt update
apt install -y ca-certificates curl git vim unzip rsync gzip

mkdir -p /opt/ttt/{app,uploads,artifacts,models,mysql,redis,backups}
```

目录说明：

| 服务器目录 | 说明 |
| --- | --- |
| `/opt/ttt/app` | GitHub 拉取的项目代码 |
| `/opt/ttt/uploads` | 用户上传、导入文件、附件 |
| `/opt/ttt/artifacts` | 训练产物、主动学习模型文件 |
| `/opt/ttt/models` | 基础嵌入模型目录 |
| `/opt/ttt/mysql` | MySQL 数据持久化目录 |
| `/opt/ttt/redis` | Redis 数据持久化目录 |
| `/opt/ttt/backups` | 数据库备份和迁移文件 |

## 4. 安装 Docker 和 Docker Compose

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" \
  > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl restart docker

docker --version
docker compose version
```

如果拉取 Docker 镜像很慢或超时，配置镜像加速：

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

## 5. 配置 CUDA 训练环境

本项目本次部署必须配置 CUDA，本节不能跳过。

### 5.1 确认宿主机 GPU 正常

```bash
nvidia-smi
```

如果提示找不到命令，先在云服务器控制台安装 NVIDIA 驱动，或者使用云厂商提供的 GPU 镜像。

### 5.2 安装 NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list

apt update
apt install -y nvidia-container-toolkit
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker
```

验证 Docker 容器能看到 GPU：

```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

只有这一步成功，后续平台训练模型才能使用 CUDA。

## 6. 从 GitHub 拉取代码

当前仓库是 public，服务器直接用 HTTPS 克隆即可，不需要 SSH key，不需要 token。

```bash
cd /opt/ttt
rm -rf app
git clone https://github.com/Tangfgjk/ttt.git app
cd /opt/ttt/app
git checkout master
git log --oneline -3
```

## 7. 上传单独文件

以下命令在 Windows PowerShell 执行。

先设置服务器 IP，后面的命令可以直接复制：

```powershell
$server = "服务器公网IP"
$src = "C:\Users\29694\Desktop\单独上传文件"
```

### 7.1 上传数据库备份

```powershell
scp "$src\db_backups\local_competency_annotation_dev_2026-06-18_190531.sql" root@$server:/opt/ttt/backups/
```

### 7.2 上传模型目录

```powershell
scp -r "$src\math_mlm_model" root@$server:/opt/ttt/models/
```

上传后服务器上应该是：

```text
/opt/ttt/models/math_mlm_model
```

不要变成：

```text
/opt/ttt/models/math_mlm_model/math_mlm_model
```

### 7.3 上传 uploads

```powershell
scp -r "$src\uploads" root@$server:/opt/ttt/
```

上传后服务器上应该是：

```text
/opt/ttt/uploads
```

### 7.4 上传 artifacts

```powershell
scp -r "$src\artifacts" root@$server:/opt/ttt/
```

上传后服务器上应该是：

```text
/opt/ttt/artifacts
```

### 7.5 在服务器检查上传结果

回到服务器终端执行：

```bash
ls -lh /opt/ttt/backups/
ls -lh /opt/ttt/models/math_mlm_model/
ls -lh /opt/ttt/uploads/
ls -lh /opt/ttt/artifacts/
```

模型目录至少应看到：

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

## 8. 配置环境变量 `.env`

服务器执行：

```bash
cd /opt/ttt/app/deploy/compose
cp .env.example .env
vim .env
```

必须修改数据库密码，示例：

```env
MYSQL_DATABASE=ttt_prod
MYSQL_USER=ttt_user
MYSQL_PASSWORD=请换成强密码
MYSQL_ROOT_PASSWORD=请换成强密码
DATABASE_URL=mysql+pymysql://ttt_user:请换成强密码@mysql:3306/ttt_prod
```

确认路径配置如下：

```env
HOST_UPLOADS_DIR=/opt/ttt/uploads
HOST_ARTIFACTS_DIR=/opt/ttt/artifacts
HOST_MODELS_DIR=/opt/ttt/models
HOST_MYSQL_DIR=/opt/ttt/mysql
HOST_REDIS_DIR=/opt/ttt/redis

IMPORT_UPLOAD_DIR=/data/uploads/imports
EMBEDDING_MODEL_PATH=/data/models/math_mlm_model
ACTIVE_LEARNING_CHECKPOINT_DIR=/data/artifacts/active_learning
```

本次部署必须使用 CUDA，把 PyTorch 配置改为：

```env
TORCH_PACKAGE=torch==2.3.1+cu121
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
```

## 9. 启动服务

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml up -d --build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml ps
```

第一次构建会比较慢。CUDA 版会下载较大的 PyTorch CUDA 文件，磁盘至少建议 80 GB。

## 10. 导入数据库

先加载 `.env`：

```bash
cd /opt/ttt/app/deploy/compose
set -a
source .env
set +a
```

导入数据库：

```bash
docker exec -i ${COMPOSE_PROJECT_NAME:-ttt}-mysql \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" \
  < /opt/ttt/backups/local_competency_annotation_dev_2026-06-18_190531.sql
```

导入完成后检查核心数据：

```bash
docker exec -it ${COMPOSE_PROJECT_NAME:-ttt}-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "
USE $MYSQL_DATABASE;
SELECT COUNT(*) AS questions FROM questions;
SELECT COUNT(*) AS question_contents FROM question_contents;
SELECT COUNT(*) AS annotations FROM annotations;
SELECT COUNT(*) AS annotation_tasks FROM annotation_tasks;
SELECT COUNT(*) AS review_tasks FROM review_tasks;
SELECT COUNT(*) AS question_embeddings FROM question_embeddings;
SELECT COUNT(*) AS users FROM users;
"
```

如果能看到题目、用户、标注任务等数量，说明数据库导入成功。

## 11. 健康检查和访问

查看容器状态：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml ps
```

正常情况下至少应看到：

```text
ttt-mysql    healthy
ttt-redis    healthy
ttt-backend  healthy
ttt-nginx    started
ttt-worker   started
```

检查后端健康接口：

```bash
curl http://127.0.0.1/api/v1/system/health
```

浏览器访问：

```text
http://服务器公网IP/
```

## 12. CUDA 验证

本次部署必须执行 CUDA 验证。

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml exec backend python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO CUDA")
PY
```

正常结果应类似：

```text
torch: 2.3.1+cu121
cuda available: True
device: NVIDIA ...
```

如果 `cuda available` 是 `False`，按顺序检查：

1. 服务器宿主机 `nvidia-smi` 是否正常。
2. `docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi` 是否正常。
3. 启动命令是否用了 `docker-compose.cuda.yml`。
4. `.env` 是否设置了 `TORCH_PACKAGE=torch==2.3.1+cu121`。
5. 修改 `.env` 后是否重新 `--build`。

## 13. 后续更新代码

以后本地代码推送到 GitHub 后，服务器只需要拉取更新并重新构建启动。服务器不需要向 GitHub 推送代码。

```bash
cd /opt/ttt/app
git pull origin master
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml up -d --build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml ps
```

注意：

- 重新构建和启动不会清空数据库。
- 数据库保存在 `/opt/ttt/mysql`。
- 上传文件保存在 `/opt/ttt/uploads`。
- 训练产物保存在 `/opt/ttt/artifacts`。

## 14. 日常数据库备份

建议每天或每次重要标注后备份一次数据库。

服务器执行：

```bash
cd /opt/ttt/app/deploy/compose
set -a
source .env
set +a

mkdir -p /opt/ttt/backups

docker exec ${COMPOSE_PROJECT_NAME:-ttt}-mysql mysqldump \
  -uroot \
  -p"$MYSQL_ROOT_PASSWORD" \
  --default-character-set=utf8mb4 \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  "$MYSQL_DATABASE" \
  | gzip > /opt/ttt/backups/ttt_prod_$(date +%F_%H%M%S).sql.gz

ls -lh /opt/ttt/backups/
```

下载到本地 Windows：

```powershell
scp root@服务器公网IP:/opt/ttt/backups/ttt_prod_最新时间.sql.gz "C:\Users\29694\Desktop\ttt\db_backups\"
```

## 15. 日常文件备份

备份 uploads：

```bash
tar -czf /opt/ttt/backups/uploads_$(date +%F_%H%M%S).tar.gz -C /opt/ttt uploads
```

备份 artifacts：

```bash
tar -czf /opt/ttt/backups/artifacts_$(date +%F_%H%M%S).tar.gz -C /opt/ttt artifacts
```

## 16. 常见问题

### 16.1 GitHub 拉取代码卡住或失败

因为仓库是 public，优先使用 HTTPS 克隆：

```bash
cd /opt/ttt
rm -rf app
git clone https://github.com/Tangfgjk/ttt.git app
```

如果 GitHub 访问非常慢，先检查服务器网络，或换用云厂商推荐的网络代理/镜像方案。不要把服务器配置成向 GitHub 推送代码。

### 16.2 Docker 镜像拉取超时

配置 `/etc/docker/daemon.json` 镜像源，然后：

```bash
systemctl restart docker
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml up -d --build
```

### 16.3 磁盘不足

查看磁盘：

```bash
df -h
docker system df
```

清理 Docker 构建缓存：

```bash
docker builder prune -f
docker image prune -f
```

如果是 CUDA 部署，40 GB 磁盘很容易不够，建议扩容。

### 16.4 模型路径错误

报错类似：

```text
No such file or directory: /data/models/math_mlm_model
```

检查：

```bash
ls -lh /opt/ttt/models/math_mlm_model
```

如果目录不存在或多套了一层，重新整理为：

```text
/opt/ttt/models/math_mlm_model/config.json
/opt/ttt/models/math_mlm_model/model.safetensors
```

### 16.5 历史训练模型找不到

报错类似：

```text
No such file or directory: /data/artifacts/active_learning/train_xxx.pth
```

说明数据库里记录了历史训练模型，但 `/opt/ttt/artifacts` 没有对应文件。

处理：

1. 确认已经上传 `C:\Users\29694\Desktop\单独上传文件\artifacts`。
2. 确认服务器路径是 `/opt/ttt/artifacts`。
3. 如果确实没有旧模型文件，可以重新训练生成新模型。

### 16.6 数据库不要公网开放

不要开放安全组 `3306`。

需要查看数据库时，在服务器执行：

```bash
cd /opt/ttt/app/deploy/compose
set -a
source .env
set +a
docker exec -it ${COMPOSE_PROJECT_NAME:-ttt}-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"
```

## 17. 最终交付检查清单

部署完成前逐项确认：

- [ ] 服务器系统是 Ubuntu 22.04 或兼容版本
- [ ] 安全组开放了 `22` 和 `80`
- [ ] 没有公网开放 `3306`、`6379`
- [ ] Docker 和 Docker Compose 安装成功
- [ ] CUDA 服务器上 `nvidia-smi` 正常
- [ ] CUDA 服务器上 Docker GPU 测试正常
- [ ] `/opt/ttt/app` 已从 GitHub 拉取 `master`
- [ ] `/opt/ttt/models/math_mlm_model` 已上传
- [ ] `/opt/ttt/uploads` 已上传
- [ ] `/opt/ttt/artifacts` 已上传
- [ ] `/opt/ttt/backups/local_competency_annotation_dev_2026-06-18_190531.sql` 已上传
- [ ] `.env` 已修改数据库密码
- [ ] Torch 已配置为 CUDA：`torch==2.3.1+cu121`
- [ ] `docker compose ps` 显示核心容器正常
- [ ] 数据库导入成功
- [ ] 浏览器能打开 `http://服务器公网IP/`
- [ ] 能登录系统并查看题目
- [ ] CUDA 部署时 `torch.cuda.is_available()` 为 `True`
- [ ] 部署完成后已做一次数据库备份
