# 新服务器 CUDA 部署交接文档

本文档给接手部署的人使用，目标是在一台新的 Ubuntu 服务器上部署 K12 学科标注平台，并支持使用 NVIDIA CUDA 训练模型。

## 1. 交接前需要准备什么

### 1.1 必备信息

- GitHub 仓库：`git@github.com:Tangfgjk/ttt.git`
- 部署分支：`master`
- 服务器系统：建议 `Ubuntu 22.04 LTS`
- 推荐配置：
  - 普通多人标注：4 vCPU / 8 GB 内存 / 40 GB 以上磁盘
  - CUDA 训练：NVIDIA GPU / 8 GB 以上显存 / 80 GB 以上磁盘，推荐 120 GB
- 对外端口：
  - `22`：SSH，仅建议放行给管理员公网 IP
  - `80`：Web 访问
  - `443`：如果后续配置 HTTPS 再放行
- 不要对公网开放：
  - `3306` MySQL
  - `6379` Redis

### 1.2 需要从旧环境带走的文件

代码从 GitHub 拉取，不需要手工复制代码目录。下面这些运行数据不会进入 GitHub，需要单独迁移：

- 数据库备份：
  - 旧服务器导出的 `ttt_prod_*.sql.gz` 或 `.sql`
  - 放到新服务器：`/opt/ttt/backups/`
- 模型目录：
  - 本项目默认目录名：`math_mlm_model`
  - 新服务器路径：`/opt/ttt/models/math_mlm_model`
  - 至少应包含：
    - `config.json`
    - `model.safetensors`
    - `tokenizer.json`
    - `tokenizer_config.json`
    - `special_tokens_map.json`
    - `vocab.txt`
    - `training_args.bin`
  - `checkpoint-*` 目录不是平台运行必需文件，只有在需要继续预训练或保留训练中间点时才上传。
- 上传文件目录：
  - 旧服务器：`/opt/ttt/uploads`
  - 新服务器：`/opt/ttt/uploads`
  - 如果题目图片、导入文件、附件都在数据库外部路径中被引用，必须迁移。
- 训练产物目录：
  - 旧服务器：`/opt/ttt/artifacts`
  - 新服务器：`/opt/ttt/artifacts`
  - 可选迁移。如果文件太大可以不上传，后续在新服务器重新训练即可。
  - 只有要继续使用旧服务器训练出的 `.pth` 模型版本时，才需要迁移。
- `.env`：
  - 旧服务器可参考，但不要提交到 GitHub。
  - 新服务器建议重新生成密码后填写。

## 2. 新服务器基础初始化

登录新服务器：

```bash
ssh root@服务器公网IP
```

更新基础工具：

```bash
apt update
apt install -y ca-certificates curl git vim unzip rsync gzip
```

创建部署目录：

```bash
mkdir -p /opt/ttt/{uploads,artifacts,models,mysql,redis,backups}
```

## 3. 安装 Docker 和 Compose

如果服务器访问 Docker 官方源较慢，可以先配置镜像源。下面是常用安装流程：

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

如果拉镜像超时，可配置 Docker 镜像加速：

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

## 4. CUDA 服务器额外准备

如果只做 CPU 部署，跳过本节。

### 4.1 确认宿主机显卡可用

```bash
nvidia-smi
```

如果没有这个命令，先在云厂商控制台安装 GPU 驱动，或按云厂商文档安装 NVIDIA Driver。必须先保证宿主机 `nvidia-smi` 正常，再继续 Docker CUDA 配置。

### 4.2 安装 NVIDIA Container Toolkit

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

验证 Docker 能看到 GPU：

```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

如果这一步失败，先不要部署项目，优先解决 GPU 驱动或 NVIDIA Container Toolkit。

## 5. 从 GitHub 拉取代码

推荐使用 SSH key。新服务器生成 key：

```bash
mkdir -p ~/.ssh
ssh-keygen -t ed25519 -C "new-server-ttt" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub
```

把输出的公钥添加到 GitHub 仓库的 Deploy keys，至少给读取权限。如果后续要从服务器直接推送代码，再给写权限；一般部署只需要读取权限。

配置 GitHub SSH：

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

拉取项目：

```bash
cd /opt/ttt
git clone git@github.com:Tangfgjk/ttt.git app
cd /opt/ttt/app
git checkout master
git log --oneline -3
```

如果没有 SSH key，也可以使用 HTTPS + GitHub Personal Access Token，但不要把 token 粘贴到文档或聊天记录里。

## 6. 配置 `.env`

```bash
cd /opt/ttt/app/deploy/compose
cp .env.example .env
vim .env
```

必须修改：

```env
MYSQL_DATABASE=ttt_prod
MYSQL_USER=ttt_user
MYSQL_PASSWORD=换成强密码
MYSQL_ROOT_PASSWORD=换成强密码
DATABASE_URL=mysql+pymysql://ttt_user:换成强密码@mysql:3306/ttt_prod
```

确认目录配置：

```env
HOST_UPLOADS_DIR=/opt/ttt/uploads
HOST_ARTIFACTS_DIR=/opt/ttt/artifacts
HOST_MODELS_DIR=/opt/ttt/models
HOST_MYSQL_DIR=/opt/ttt/mysql
HOST_REDIS_DIR=/opt/ttt/redis
EMBEDDING_MODEL_PATH=/data/models/math_mlm_model
ACTIVE_LEARNING_CHECKPOINT_DIR=/data/artifacts/active_learning
```

CPU 部署保持默认：

```env
TORCH_PACKAGE=torch==2.3.1+cpu
TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
```

CUDA 部署改成：

```env
TORCH_PACKAGE=torch==2.3.1+cu121
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121
```

说明：

- 代码依赖约束是 `torch>=2.2,<2.4`，所以这里固定使用 `torch==2.3.1`。
- `cu121` 需要服务器 NVIDIA 驱动支持 CUDA 12.1 运行时。云服务器一般使用较新的驱动即可。
- 如果云厂商提供的是其他 CUDA 版本，优先以 PyTorch 官方安装选择器给出的 wheel 地址为准。

## 7. 上传模型、数据库和运行数据

### 7.1 上传模型目录

Windows PowerShell 示例：

```powershell
scp -r "C:\path\to\math_mlm_model" root@服务器公网IP:/opt/ttt/models/
```

服务器检查：

```bash
ls -lh /opt/ttt/models/math_mlm_model
```

至少要看到 `model.safetensors`、`config.json`、`tokenizer.json` 等文件。

### 7.2 上传数据库备份

Windows PowerShell 示例：

```powershell
scp "C:\Users\29694\Desktop\ttt\db_backups\ttt_prod_最新备份.sql.gz" root@服务器公网IP:/opt/ttt/backups/
```

服务器检查压缩包完整性：

```bash
gzip -t /opt/ttt/backups/ttt_prod_最新备份.sql.gz
ls -lh /opt/ttt/backups/
```

### 7.3 上传 uploads；artifacts 可选

如果旧服务器上已有题目附件，建议迁移 `uploads`。`artifacts` 是历史训练产物，文件较大时可以不迁移，后续在新服务器重新训练即可。

```bash
# 在旧服务器执行，打包
tar -czf /opt/ttt/backups/uploads_$(date +%F_%H%M%S).tar.gz -C /opt/ttt uploads
tar -czf /opt/ttt/backups/artifacts_$(date +%F_%H%M%S).tar.gz -C /opt/ttt artifacts
```

下载到本地后再上传到新服务器，或使用 `scp` 在两台服务器之间传输。

在新服务器解压：

```bash
tar -xzf /opt/ttt/backups/uploads_xxx.tar.gz -C /opt/ttt
tar -xzf /opt/ttt/backups/artifacts_xxx.tar.gz -C /opt/ttt
```

如果不迁移 `artifacts`，跳过 artifacts 打包和解压命令即可。

## 8. 首次构建和启动

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

第一次构建 CUDA 镜像会下载较大的 PyTorch CUDA wheel，时间可能较长，也更占磁盘。不要在构建中途频繁中断。

## 9. 导入数据库

如果是首次部署并要导入完整备份，先启动容器，再导入 SQL。

```bash
cd /opt/ttt/app/deploy/compose
set -a
source .env
set +a
```

导入 `.sql.gz`：

```bash
gunzip -c /opt/ttt/backups/ttt_prod_最新备份.sql.gz \
  | docker exec -i ${COMPOSE_PROJECT_NAME:-ttt}-mysql \
      mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"
```

导入普通 `.sql`：

```bash
docker exec -i ${COMPOSE_PROJECT_NAME:-ttt}-mysql \
  mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" \
  < /opt/ttt/backups/ttt_prod_最新备份.sql
```

导入后检查核心表：

```bash
docker exec -it ${COMPOSE_PROJECT_NAME:-ttt}-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "
USE $MYSQL_DATABASE;
SELECT COUNT(*) AS questions FROM questions;
SELECT COUNT(*) AS annotations FROM annotations;
SELECT COUNT(*) AS annotation_tasks FROM annotation_tasks;
SELECT COUNT(*) AS review_tasks FROM review_tasks;
SELECT COUNT(*) AS question_embeddings FROM question_embeddings;
SELECT COUNT(*) AS users FROM users;
"
```

## 10. 健康检查

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 backend
docker compose --env-file .env logs --tail=100 nginx
curl http://127.0.0.1/api/v1/system/health
```

浏览器打开：

```text
http://服务器公网IP/
```

如果配置了域名和 HTTPS，再使用域名访问。

## 11. CUDA 验证

CUDA 部署完成后，在容器内检查 PyTorch：

```bash
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml exec backend python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NO CUDA")
PY
```

结果应类似：

```text
torch: 2.3.1+cu121
cuda available: True
device: NVIDIA ...
```

如果 `cuda available` 是 `False`，按下面顺序排查：

1. 宿主机 `nvidia-smi` 是否正常。
2. `docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi` 是否正常。
3. 启动命令是否使用了 `-f docker-compose.yml -f docker-compose.cuda.yml`。
4. `.env` 是否设置了 `TORCH_PACKAGE=torch==2.3.1+cu121` 和 `TORCH_INDEX_URL=https://download.pytorch.org/whl/cu121`。
5. 是否重新 `--build` 过后端镜像。

## 12. 训练模型时怎么用 CUDA

在系统管理员界面进入“训练模型”：

- 训练设备选择 `自动`：有 CUDA 时自动用 GPU，没有时用 CPU。
- 训练设备选择 `cuda`：强制使用 GPU，如果容器无法访问 CUDA，会直接报错。
- 训练输出保存在：`/opt/ttt/artifacts/active_learning`
- 模型目录挂载到容器内：`/data/models`

建议新服务器首次验证时先用较小训练轮数测试，确认能正常开始、日志无 CUDA 报错，再运行正式训练。

## 13. 后续更新代码和重新部署

普通 CPU 部署：

```bash
cd /opt/ttt/app
git pull origin master
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env up -d --build
docker compose --env-file .env ps
```

CUDA 部署：

```bash
cd /opt/ttt/app
git pull origin master
cd /opt/ttt/app/deploy/compose
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml up -d --build
docker compose --env-file .env -f docker-compose.yml -f docker-compose.cuda.yml ps
```

如果只是前端或后端代码改动，数据库数据不会因为重新构建容器丢失。MySQL 数据保存在宿主机目录 `HOST_MYSQL_DIR=/opt/ttt/mysql`。

## 14. 日常备份

### 14.1 备份数据库

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

### 14.2 备份 uploads 和 artifacts

```bash
tar -czf /opt/ttt/backups/uploads_$(date +%F_%H%M%S).tar.gz -C /opt/ttt uploads
tar -czf /opt/ttt/backups/artifacts_$(date +%F_%H%M%S).tar.gz -C /opt/ttt artifacts
```

### 14.3 下载备份到本地

Windows PowerShell：

```powershell
scp root@服务器公网IP:/opt/ttt/backups/ttt_prod_最新备份.sql.gz C:\Users\29694\Desktop\ttt\db_backups\
scp root@服务器公网IP:/opt/ttt/backups/uploads_最新备份.tar.gz C:\Users\29694\Desktop\ttt\db_backups\
scp root@服务器公网IP:/opt/ttt/backups/artifacts_最新备份.tar.gz C:\Users\29694\Desktop\ttt\db_backups\
```

## 15. 常见问题

### 15.1 Docker 拉镜像超时

现象：

```text
failed to resolve reference docker.io/...
i/o timeout
```

处理：

1. 配置 `/etc/docker/daemon.json` 镜像源。
2. `systemctl restart docker`。
3. 重新执行 `docker compose ... up -d --build`。

### 15.2 CUDA 构建时磁盘不足

现象：

```text
no space left on device
```

处理：

```bash
df -h
docker system df
docker builder prune -f
docker image prune -f
```

如果仍不足，扩容系统盘。CUDA 版 PyTorch 和构建缓存很大，40 GB 系统盘通常偏紧。

### 15.3 容器健康检查失败

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=200 backend
docker compose --env-file .env logs --tail=200 mysql
```

重点检查：

- `.env` 中 `DATABASE_URL` 的用户名、密码、库名是否和 MySQL 配置一致。
- MySQL 是否导入了数据。
- 后端是否提示模型路径不存在。

### 15.4 模型路径不存在

现象：

```text
No such file or directory: /data/models/math_mlm_model
```

处理：

```bash
ls -lh /opt/ttt/models/math_mlm_model
```

如果目录不存在，把本地 `math_mlm_model` 上传到 `/opt/ttt/models/`，不要上传到 `/opt/ttt/app/` 里面。

### 15.5 历史训练模型 `.pth` 找不到

现象：

```text
No such file or directory: /data/artifacts/active_learning/train_xxx.pth
```

说明：

- 数据库里记录了某个历史模型版本。
- 但是对应 `.pth` 文件没有迁移到新服务器。

处理：

1. 如果必须使用旧模型，从旧服务器迁移 `/opt/ttt/artifacts/active_learning`。
2. 如果不需要旧模型，可以忽略旧记录，重新训练模型生成新的模型版本。

### 15.6 MySQL 不要直接公网开放

不要为了 Navicat 方便而开放安全组 `3306`。如果确实要查数据库，优先使用 SSH 登录服务器后执行：

```bash
cd /opt/ttt/app/deploy/compose
set -a
source .env
set +a
docker exec -it ${COMPOSE_PROJECT_NAME:-ttt}-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"
```

如果必须用 Navicat，建议使用 SSH 隧道，不要开放公网 MySQL。

## 16. 新服务器交付检查清单

- [ ] 安全组只开放必要端口：`22`、`80`、可选 `443`
- [ ] `/opt/ttt/app` 已从 GitHub `master` 拉取最新代码
- [ ] `/opt/ttt/models/math_mlm_model` 已上传
- [ ] `/opt/ttt/uploads` 已按需要迁移
- [ ] `/opt/ttt/artifacts` 已创建；如不迁移旧训练模型，可以为空，后续训练会生成新文件
- [ ] `/opt/ttt/backups` 中有本次导入的数据库备份
- [ ] `.env` 已配置强密码，且未提交到 GitHub
- [ ] `docker compose ps` 中 `mysql`、`redis`、`backend`、`nginx` 均正常
- [ ] 浏览器能打开 `http://服务器公网IP/`
- [ ] 能登录系统并查看题目
- [ ] CUDA 部署时，容器内 `torch.cuda.is_available()` 返回 `True`
- [ ] 已做一次部署后数据库备份
