# V11 部署文档

`docs/design/v11/` 用于记录本项目云服务器部署后的正式部署与运维经验。这里保留历史部署记录，实际交接和新服务器部署优先查看 `deploy/` 目录下的操作文档。

## 文档列表

1. [V11-部署文档V1.md](./V11-部署文档V1.md)
   - 首次阿里云 ECS + Docker Compose 部署记录、故障处理和运维命令沉淀。
2. [新服务器 CUDA 部署交接文档](../../../deploy/NEW_SERVER_CUDA_DEPLOYMENT.md)
   - 面向新接手部署人员的完整流程，包含 GitHub 拉取代码、上传模型和数据库、CUDA 环境、重新部署、备份与排错。

## 当前部署基线

- 代码来源：GitHub `Tangfgjk/ttt` 仓库 `master` 分支。
- 正式运行方式：Docker Compose。
- 数据库：MySQL 容器，宿主机目录持久化。
- 模型和训练产物：不进入 GitHub，需要通过 `/opt/ttt/models` 和 `/opt/ttt/artifacts` 单独迁移。
- CUDA：默认镜像是 CPU PyTorch；新服务器如需 GPU 训练，使用 `deploy/compose/docker-compose.cuda.yml` 和 CUDA 版 PyTorch 构建参数。
