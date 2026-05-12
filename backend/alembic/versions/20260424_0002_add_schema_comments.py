"""Add MySQL table and column comments for the initial schema."""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op


revision = "20260424_0002"
down_revision = "20260424_0001"
branch_labels = None
depends_on = None


TABLE_COMMENTS = {
    "alembic_version": "Alembic 迁移版本记录表",
    "subjects": "学科字典表",
    "grades": "年级字典表",
    "question_types": "题型字典表",
    "cognitive_levels": "认知层级字典表",
    "competencies": "核心素养字典表",
    "knowledge_types": "知识点类型字典表",
    "textbooks": "教材字典表",
    "catalogs": "教材目录表",
    "roles": "角色表",
    "permissions": "权限表",
    "role_permissions": "角色权限关联表",
    "users": "系统用户表",
    "learning_modules": "培训学习模块表",
    "learning_records": "用户学习进度记录表",
    "data_sources": "外部数据源定义表",
    "import_batches": "数据导入批次表",
    "source_question_records": "原始导入记录表",
    "questions": "题目主表",
    "question_external_refs": "题目外部编号映射表",
    "question_contents": "题目正文与答案内容表",
    "question_subquestions": "题目子题表",
    "question_assets": "题目资源附件表",
    "question_knowledge_points": "题目知识点关联表",
    "question_catalogs": "题目教材目录关联表",
    "question_gold_labels": "题目金标准标签表",
    "question_gold_competencies": "金标准核心素养明细表",
    "classes": "班级表",
    "students": "学生表",
    "exams": "考试表",
    "exam_questions": "考试题目关联表",
    "student_exam_scores": "学生考试总分表",
    "student_question_responses": "学生题目作答明细表",
    "annotation_tasks": "标注任务表",
    "annotations": "人工标注记录表",
    "annotation_competencies": "标注核心素养明细表",
    "annotation_knowledge_points": "标注知识点明细表",
    "question_label_aggregates": "题目聚合标签结果表",
    "question_aggregate_competencies": "聚合核心素养明细表",
    "review_tasks": "争议复核任务表",
    "embedding_models": "嵌入模型定义表",
    "question_embeddings": "题目向量表",
    "recommendation_batches": "推荐批次表",
    "recommendation_items": "推荐结果明细表",
    "coreset_experiments": "Coreset 实验评估表",
    "model_versions": "模型版本表",
    "training_datasets": "训练数据集版本表",
    "training_tasks": "模型训练任务表",
    "audit_logs": "系统审计日志表",
}

COMMON_COLUMN_COMMENTS = {
    "id": "主键ID",
    "code": "业务编码",
    "name": "名称",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "user_id": "用户ID",
    "question_id": "题目ID",
    "grade_id": "年级ID",
    "subject_id": "学科ID",
    "created_by": "创建人用户ID",
}

TABLE_COLUMN_COMMENTS = {
    "alembic_version": {
        "version_num": "当前数据库迁移版本号",
    },
    "subjects": {
        "code": "学科编码，如 math",
        "name": "学科名称",
        "is_active": "是否启用",
    },
    "grades": {
        "grade_index": "年级数字编号，如 7/8/9",
        "grade_code": "年级编码",
        "grade_name": "年级名称",
        "edu_stage": "学段编码",
    },
    "question_types": {
        "code": "题型编码",
        "name": "题型名称",
        "base_type_index": "来源侧基础题型编号",
    },
    "cognitive_levels": {
        "code": "认知层级编码",
        "name": "认知层级名称",
        "level_order": "认知层级顺序",
    },
    "competencies": {
        "code": "核心素养编码",
        "name": "核心素养名称",
        "display_order": "展示顺序",
    },
    "knowledge_types": {
        "source_type_code": "来源知识类型编码",
        "source_type_name": "来源知识类型名称",
    },
    "textbooks": {
        "source_textbook_id": "来源教材ID",
    },
    "catalogs": {
        "source_catalog_id": "来源目录ID",
        "textbook_id": "教材ID",
        "parent_id": "父级目录ID",
        "school_code": "学校编码",
    },
    "roles": {
        "code": "角色编码",
    },
    "permissions": {
        "code": "权限编码",
    },
    "role_permissions": {
        "role_id": "角色ID",
        "permission_id": "权限ID",
    },
    "users": {
        "username": "登录用户名",
        "email": "邮箱",
        "password_hash": "密码哈希",
        "role_id": "角色ID",
        "real_name": "真实姓名",
        "is_active": "是否启用",
        "is_verified": "是否通过培训",
        "last_login_at": "最后登录时间",
    },
    "learning_modules": {
        "code": "培训模块编码",
        "title": "培训模块标题",
        "sort_order": "排序值",
    },
    "learning_records": {
        "module_id": "培训模块ID",
        "progress_percent": "学习进度百分比",
        "is_completed": "是否已完成",
        "completed_at": "完成时间",
    },
    "data_sources": {
        "code": "数据源编码",
        "source_type": "数据源类型，如 excel/json/api",
        "description": "数据源说明",
    },
    "import_batches": {
        "data_source_id": "数据源ID",
        "batch_no": "导入批次号",
        "file_name": "导入文件名",
        "import_status": "导入状态",
        "total_records": "总记录数",
        "success_records": "成功记录数",
        "failed_records": "失败记录数",
        "error_message": "导入错误信息",
        "finished_at": "导入完成时间",
    },
    "source_question_records": {
        "import_batch_id": "导入批次ID",
        "data_source_id": "数据源ID",
        "source_record_key": "来源记录主键",
        "record_type": "记录类型，如 question/exam_response",
        "raw_payload": "原始记录JSON",
        "normalized_hash": "归一化哈希值",
        "parse_status": "解析状态",
        "error_message": "解析错误信息",
    },
    "questions": {
        "question_type_id": "题型ID",
        "difficulty_level": "难度等级",
        "blank_count": "填空数量",
        "has_subquestions": "是否有子题",
        "source_status": "来源状态",
        "annotation_status": "标注状态",
        "required_annotations": "所需标注人数",
        "annotation_count": "已完成标注人数",
        "latest_embedding_version": "最新嵌入版本号",
    },
    "question_external_refs": {
        "data_source_id": "数据源ID",
        "external_question_id": "外部题目ID",
        "external_type": "外部题型编码",
        "is_primary": "是否主映射",
    },
    "question_contents": {
        "stem_text": "题干纯文本",
        "stem_html": "题干HTML或MathML",
        "answer_text": "标准答案文本",
        "solution_text": "解析文本",
        "source_content_hash": "内容哈希",
    },
    "question_subquestions": {
        "sub_no": "子题序号",
        "stem_text": "子题题干纯文本",
        "stem_html": "子题题干HTML",
        "answer_text": "子题答案",
        "score": "子题分值",
    },
    "question_assets": {
        "subquestion_id": "子题ID",
        "asset_type": "资源类型",
        "asset_url": "原始资源URL",
        "storage_key": "对象存储键",
        "sort_order": "显示顺序",
    },
    "question_knowledge_points": {
        "knowledge_point_id": "知识点ID",
        "priority": "优先级",
        "is_core": "是否核心知识点",
        "is_exam_point": "是否考点",
        "is_last_exam_point": "是否末级考点",
        "sort_index": "来源排序号",
    },
    "question_catalogs": {
        "catalog_id": "目录ID",
        "school_code": "学校编码",
    },
    "question_gold_labels": {
        "source_record_id": "来源原始记录ID",
        "cognitive_level_id": "金标准认知层级ID",
        "label_source": "标签来源",
        "imported_at": "导入时间",
    },
    "question_gold_competencies": {
        "gold_label_id": "金标准标签ID",
        "competency_id": "核心素养ID",
        "level_value": "核心素养层级值",
    },
    "classes": {
        "source_class_id": "来源班级ID",
        "class_name": "班级名称",
        "class_seq": "班级序号",
    },
    "students": {
        "source_student_id": "来源学生编号",
        "student_name": "学生姓名",
        "class_id": "班级ID",
    },
    "exams": {
        "source_exam_id": "来源考试ID",
        "exam_code": "考试编号",
        "exam_name": "考试名称",
        "exam_type": "考试类型",
        "term_name": "学期名称",
        "exam_time": "考试时间",
        "total_score": "考试总分",
    },
    "exam_questions": {
        "exam_id": "考试ID",
        "question_no": "题号",
        "custom_question_no": "自定义题号",
        "score": "题目分值",
    },
    "student_exam_scores": {
        "exam_id": "考试ID",
        "student_id": "学生ID",
        "class_id": "班级ID",
        "total_score": "考试总分",
    },
    "student_question_responses": {
        "exam_id": "考试ID",
        "student_id": "学生ID",
        "response_text": "学生作答内容",
        "response_score": "该题得分",
        "subquestion_answer_text": "子题答案内容",
    },
    "annotation_tasks": {
        "assignee_id": "标注员用户ID",
        "source_batch_id": "推荐批次ID",
        "task_status": "任务状态",
        "assigned_at": "分配时间",
        "started_at": "开始时间",
        "submitted_at": "提交时间",
    },
    "annotations": {
        "task_id": "标注任务ID",
        "version_no": "版本号",
        "cognitive_level_id": "认知层级ID",
        "confidence_level": "标注自信度",
        "time_spent_seconds": "标注耗时秒数",
        "is_final": "是否最终版本",
        "annotation_status": "标注状态",
    },
    "annotation_competencies": {
        "annotation_id": "标注记录ID",
        "competency_id": "核心素养ID",
        "level_value": "核心素养层级值",
    },
    "annotation_knowledge_points": {
        "annotation_id": "标注记录ID",
        "knowledge_point_id": "知识点ID",
    },
    "question_label_aggregates": {
        "final_cognitive_level_id": "最终认知层级ID",
        "agreement_score": "一致性分数",
        "is_disputed": "是否存在争议",
        "completed_annotation_count": "已完成标注数",
        "finalized_at": "聚合完成时间",
    },
    "question_aggregate_competencies": {
        "aggregate_id": "聚合结果ID",
        "competency_id": "核心素养ID",
        "level_value": "聚合层级值",
        "agreement_score": "该素养一致性分数",
    },
    "review_tasks": {
        "aggregate_id": "聚合结果ID",
        "reviewer_id": "复核员用户ID",
        "review_status": "复核状态",
        "review_comment": "复核意见",
        "reviewed_at": "复核完成时间",
    },
    "embedding_models": {
        "model_code": "嵌入模型编码",
        "model_name": "嵌入模型名称",
        "dimension": "向量维度",
        "is_active": "是否启用",
    },
    "question_embeddings": {
        "embedding_model_id": "嵌入模型ID",
        "vector_json": "向量JSON数据",
        "vector_norm": "向量范数",
        "computed_at": "计算时间",
    },
    "recommendation_batches": {
        "batch_no": "推荐批次号",
        "algorithm_code": "算法编码",
        "triggered_by_user_id": "触发人用户ID",
        "target_stage": "推荐阶段",
        "context_json": "推荐上下文JSON",
    },
    "recommendation_items": {
        "batch_id": "推荐批次ID",
        "score": "推荐分数",
        "rank_no": "排序名次",
        "is_accepted": "是否被采纳",
    },
    "coreset_experiments": {
        "batch_id": "推荐批次ID",
        "algorithm_code": "算法编码",
        "params_json": "实验参数JSON",
        "metrics_json": "实验指标JSON",
        "selected_question_count": "选中题目数量",
    },
    "model_versions": {
        "version_code": "模型版本编码",
        "model_type": "模型类型",
        "base_model_name": "基础模型名称",
        "artifact_path": "模型产物路径",
        "metrics_json": "模型指标JSON",
    },
    "training_datasets": {
        "dataset_code": "训练数据集编码",
        "sample_count": "样本数量",
        "dataset_config_json": "训练数据集配置JSON",
    },
    "training_tasks": {
        "task_no": "训练任务编号",
        "dataset_id": "训练数据集ID",
        "model_version_id": "输出模型版本ID",
        "task_status": "任务状态",
        "queue_name": "队列名称",
        "celery_task_id": "Celery任务ID",
        "hyperparams_json": "超参数JSON",
        "metrics_json": "训练指标JSON",
        "started_at": "开始时间",
        "finished_at": "结束时间",
    },
    "audit_logs": {
        "module_code": "模块编码",
        "action_code": "操作编码",
        "target_type": "目标类型",
        "target_id": "目标ID",
        "detail_json": "审计详情JSON",
    },
}


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _quote_default(column_type: str, default_value: object) -> str:
    if default_value is None:
        return "DEFAULT NULL"

    raw = str(default_value)
    lower = raw.lower()

    if "current_timestamp" in lower:
        return f"DEFAULT {raw}"

    numeric_markers = (
        "int",
        "decimal",
        "float",
        "double",
        "tinyint",
        "smallint",
        "mediumint",
        "bigint",
        "bit",
    )
    if any(marker in column_type.lower() for marker in numeric_markers):
        return f"DEFAULT {raw}"

    if lower in {"true", "false"}:
        return f"DEFAULT {raw.upper()}"

    return f"DEFAULT '{_escape(raw)}'"


def _build_extra(extra: str | None) -> str:
    if not extra:
        return ""

    extra_lower = extra.lower()
    pieces: list[str] = []
    if "auto_increment" in extra_lower:
        pieces.append("AUTO_INCREMENT")
    if "on update current_timestamp" in extra_lower:
        pieces.append("ON UPDATE CURRENT_TIMESTAMP")
    return " ".join(pieces)


def _iter_table_columns(connection, table_name: str) -> Iterable[dict]:
    result = connection.exec_driver_sql(f"SHOW FULL COLUMNS FROM `{table_name}`")
    for row in result.mappings():
        yield row


def _build_modify_sql(table_name: str, column: dict, comment: str) -> str:
    parts = [f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column['Field']}` {column['Type']}"]

    if column.get("Collation"):
        parts.append(f"COLLATE {column['Collation']}")

    if column["Null"] == "NO":
        parts.append("NOT NULL")
    else:
        parts.append("NULL")

    default_clause = _quote_default(column["Type"], column.get("Default"))
    if default_clause != "DEFAULT NULL" or column["Null"] == "YES":
        parts.append(default_clause)

    extra_clause = _build_extra(column.get("Extra"))
    if extra_clause:
        parts.append(extra_clause)

    parts.append(f"COMMENT '{_escape(comment)}'")
    return " ".join(parts)


def _apply_table_comment(connection, table_name: str, comment: str) -> None:
    connection.exec_driver_sql(f"ALTER TABLE `{table_name}` COMMENT = '{_escape(comment)}'")


def _apply_column_comment(connection, table_name: str, column_name: str, comment: str) -> None:
    for column in _iter_table_columns(connection, table_name):
        if column["Field"] == column_name:
            connection.exec_driver_sql(_build_modify_sql(table_name, column, comment))
            return


def upgrade() -> None:
    connection = op.get_bind()

    for table_name, comment in TABLE_COMMENTS.items():
        _apply_table_comment(connection, table_name, comment)

    for table_name, table_comment_map in TABLE_COLUMN_COMMENTS.items():
        for column_name, comment in table_comment_map.items():
            _apply_column_comment(connection, table_name, column_name, comment)

        for column in _iter_table_columns(connection, table_name):
            column_name = column["Field"]
            if column_name in table_comment_map:
                continue
            common_comment = COMMON_COLUMN_COMMENTS.get(column_name)
            if common_comment:
                _apply_column_comment(connection, table_name, column_name, common_comment)


def downgrade() -> None:
    connection = op.get_bind()

    for table_name in TABLE_COMMENTS:
        _apply_table_comment(connection, table_name, "")
        for column in _iter_table_columns(connection, table_name):
            _apply_column_comment(connection, table_name, column["Field"], "")
