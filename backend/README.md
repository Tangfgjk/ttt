# Backend Skeleton

这个目录是项目后端的第一版工程骨架，目标不是一次性把全部业务写完，而是先搭出一套可长期演进的底座。

## 当前已包含

- `FastAPI` 应用入口与路由注册
- `Pydantic Settings` 配置体系
- `SQLAlchemy 2.x` 数据库引擎与会话工厂
- `Alembic` 初始迁移骨架
- `Celery` 应用初始化
- 基础响应模型、异常模型与健康检查接口
- 目录分层约定，便于后续继续补业务模块

## 目录说明

- `app/api`
  - HTTP 路由层
- `app/core`
  - 配置、日志、异常、应用级通用能力
- `app/db`
  - `SQLAlchemy` Base、会话和数据库底层配置
- `app/models`
  - ORM 模型定义
- `app/schemas`
  - 请求/响应 DTO
- `app/services`
  - 业务服务层
- `app/repositories`
  - 数据访问层
- `app/tasks`
  - Celery 与异步任务
- `alembic`
  - 数据库迁移

## 运行建议

1. 先复制环境变量模板

```bash
cp .env.example .env
```

2. 安装依赖

```bash
pip install -e .[dev]
```

3. 执行数据库迁移

```bash
alembic upgrade head
```

4. 启动服务

```bash
uvicorn app.main:app --reload
```

## 当前阶段的取舍

- 现在先把“运行骨架 + 迁移基线”搭稳
- ORM 模型会按模块逐步补齐，不强行一次写满 49 张表
- Alembic 初始版本先执行整理后的 SQL 文件，后续字段迭代再转为标准 revision 增量演进

## 下一步建议

- 先补 `dictionary`、`question_bank`、`annotation` 的 ORM 与 API
- 再接导入器、标注闭环、推荐与训练模块
