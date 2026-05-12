# Alembic 初始迁移说明

当前目录放的是 V2 设计阶段准备好的 Alembic 初始迁移骨架：

- `versions/20260424_0001_init_schema.py`
  - Alembic revision 脚本
  - 负责执行配套的 SQL 文件
- `sql/20260424_0001_upgrade.sql`
  - 初始建表与种子数据
- `sql/20260424_0001_downgrade.sql`
  - 按依赖逆序删除表

这样拆分的目的：

- 避免首版迁移文件因为 49 张表而过度膨胀
- 保留原始 SQL 的可读性
- 后续新增字段、索引、表时，再逐步使用标准 Alembic revision 追加即可

后续接入 Alembic 时，建议命令流程：

```bash
alembic init backend/alembic
alembic upgrade head
```

注意：

- 当前仓库还没有完整的 `alembic.ini`、`env.py` 和 SQLAlchemy 模型绑定
- 这版文件的定位是“初始迁移基线”，用于后续搭建后端骨架时直接接上
