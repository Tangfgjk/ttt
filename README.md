# K12 学科标注平台

K12 学科标注平台是一个面向 K12 多学科题目的导入、判重、培训、多人标注、复核、主动学习选题与训练监控的一体化系统。

当前版本定位为“一阶段初版系统”：核心业务链路已经基本打通，适合用于本地演示、阶段汇报、功能验证和后续迭代开发。

## 核心能力

- 题库导入：支持 Excel/文件夹批量导入、导入批次记录、重复题候选识别与人工复核。
- 统一题池：集中管理题目状态、来源、学段、学科、标注状态和批次信息。
- 标注员培训与准入：支持初中/高中培训、基础知识引导、单题实战校准、结果复盘、错题重做和历史记录选择。
- 多人并行标注：支持多标注员领取题目、同题按 `1/2/3` 人策略标注、实时更新个人工作台数据。
- 一致性与复核：按素养维度和层级进行一致性判定；有争议题自动进入复核员队列。
- 复核员工作流：支持领取复核题、查看三人标注情况、提交最终复核结论、查看已复核记录。
- 管理后台：支持标注策略切换、题池治理、批次撤回、审核日志、操作历史、CoreSet 历史任务和失败原因查看。
- 主动学习闭环：支持模型训练、低置信度预测选题、CoreSet 全量/增量选题、训练日志和训练监控。
- 试题嵌入可视化：基于题目 embedding 做 PCA/降维展示，辅助观察题库分布和标注状态。

## 技术栈

- 后端：Python 3.11、FastAPI、SQLAlchemy、Alembic、Pydantic、Celery、Redis、MySQL。
- 前端：React 18、TypeScript、Vite、Ant Design、React Query、Zustand、ECharts。
- 机器学习：PyTorch、Transformers、scikit-learn、题目 embedding、主动学习选题策略。

## 目录结构

```text
ttt/
├── backend/              # FastAPI 后端服务、数据库模型、业务服务、任务队列
├── deploy/               # Docker Compose、Dockerfile、Nginx 等部署资产
├── frontend/             # React 前端工程
├── docs/design/          # 阶段设计、汇报、操作文档
├── MLM/                  # 本地预训练模型或 embedding 模型目录
├── uploads/              # 导入文件与运行时上传目录
└── RUN_LOCAL_NOTES.md    # 本地跑通记录
```

## 本地启动

### 1. 后端环境

```powershell
cd C:\Users\29694\Desktop\ttt\backend
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

后端配置文件为 `backend/.env`，关键配置包括：

```env
APP_ENV=local
API_V1_PREFIX=/api/v1
DATABASE_URL=mysql+pymysql://root:your_password@127.0.0.1:3306/competency_annotation_dev
REDIS_URL=redis://127.0.0.1:6379/0
EMBEDDING_MODEL_PATH=C:/Users/29694/Desktop/ttt/MLM/rePretrain.zip/rePretrain/math_mlm_model
ACTIVE_LEARNING_GPU_WORKER_PYTHON=D:/anaconda3/envs/ttt_gpu311/python.exe
```

启动后端：

```powershell
cd C:\Users\29694\Desktop\ttt\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

如果使用 `8000` 端口也可以，但需要确保前端代理指向同一端口。

### 2. 前端环境

```powershell
cd C:\Users\29694\Desktop\ttt\frontend
npm.cmd install
```

如后端运行在 `8001`，前端启动时设置：

```powershell
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:8001"
npm.cmd run dev
```

访问地址：

```text
http://127.0.0.1:5173
```

## 开发账号

系统包含开发演示账号，首次登录时会自动初始化或由现有数据库提供：

| 角色 | 用户名 | 密码 | 主要入口 |
| --- | --- | --- | --- |
| 系统管理员 | `admin` | `admin123` | 项目总览、导入中心、判重复核、统一题池、可视化、管理后台、训练监控 |
| 标注员 | `annotator` / `annotator_dev_1` | `annotator123` | 我的工作台、培训准入、标注工作台、我的标注记录 |
| 复核员 | `reviewer` | `reviewer123` | 我的工作台、标注复核、已复核题目 |

实际可用账号以当前数据库为准。

## 标注策略说明

管理员可在“管理后台 -> 标注策略控制台”切换 `1 人 / 2 人 / 3 人` 标注模式。

- 系统级当前策略存储在 `system_config_entries.annotation_policy`。
- 新导入题目会直接继承当前策略，并写入 `questions.required_annotations`。
- 切换策略后，系统会在后台同步当前尚未开工的题目，并在管理后台显示“后台同步中 / 已完成 / 失败”状态。

当前后台同步只会处理同时满足以下条件的题目：

- `source_status = ACTIVE`
- `annotation_status` 属于 `PENDING` 或 `WAITING`
- `annotation_count = 0`
- `required_annotations != 当前新策略`

以下题目不会被这次策略切换回填影响：

- 已经进入 `IN_PROGRESS` 的题目
- 已进入 `REVIEW_PENDING` 的题目
- 已完成并进入 `COMPLETED` 的题目
- 已经被复核员定稿并回到已标注池的题目

也就是说，策略切换会影响未来新题和当前还没开工的题，不会打断已经在标注或复核流程中的题目。

## 验证命令

后端测试：

```powershell
cd C:\Users\29694\Desktop\ttt
backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

前端构建：

```powershell
cd C:\Users\29694\Desktop\ttt\frontend
npm.cmd run build
```

## 重要文档

- [V7 文档索引](docs/design/v7/README.md)
- [V7 Docker Compose 部署设计方案](docs/design/v7/V7-Docker%20Compose%20部署设计方案.md)
- [V7 Docker Compose 实施草案](docs/design/v7/V7-Docker%20Compose%20实施草案.md)
- [V7 服务器部署操作手册](docs/design/v7/V7-%E6%9C%8D%E5%8A%A1%E5%99%A8%E9%83%A8%E7%BD%B2%E6%93%8D%E4%BD%9C%E6%89%8B%E5%86%8C.md)
- [部署资产说明](deploy/README.md)
- [V6 文档索引](docs/design/v6/README.md)
- [V6 一阶段初版系统操作手册](docs/design/v6/V6-一阶段初版系统操作手册.md)
- [V6 一阶段收尾总结](docs/design/v6/V6-一阶段收尾总结.md)
- [V6 近期工作汇报](docs/design/v6/V6-近期工作汇报.md)
- [V5 多人标注一致性判定与审核日志设计](docs/design/v5/V5-多人标注一致性判定与审核日志设计.md)
- [V5 CoreSet 增量更新与历史任务治理设计](docs/design/v5/V5-CoreSet增量更新与历史任务治理设计.md)

## 当前阶段结论

项目一阶段已经完成初版系统的主体能力建设：题库导入、判重、培训准入、多人标注、复核、管理治理、主动学习训练、CoreSet 选题和可视化均已具备可运行版本。

后续二阶段建议重点放在正式评测、权限安全、生产部署、算法指标可解释性和更细粒度的数据治理上。
