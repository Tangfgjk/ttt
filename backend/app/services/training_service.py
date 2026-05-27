from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    AnnotatorTrainingAttempt,
    QuestionAggregateCompetency,
    QuestionGoldCompetency,
    QuestionGoldLabel,
    QuestionLabelAggregate,
)
from app.models.auth import User
from app.models.dictionary import Competency, Grade
from app.models.question import Question
from app.schemas.training import (
    TrainingAttemptResponse,
    TrainingCompetencyDefinition,
    TrainingGuideExampleCompetencyOut,
    TrainingGuideExampleOut,
    TrainingModuleResponse,
    TrainingQuestionCompetencyResult,
    TrainingQuestionOut,
    TrainingQuestionResult,
    TrainingStage,
    TrainingStatusResponse,
    TrainingSubmitRequest,
    TrainingSubmitResponse,
)
from app.services.training_examples import (
    JUNIOR_CALIBRATION_QUESTION_IDS,
    JUNIOR_EXAMPLE_GUIDANCE,
    JUNIOR_GUIDE_EXAMPLE_IDS,
)
from app.services.question_content_hydrator import hydrate_question_contents

PASS_THRESHOLD = 80

TRAINING_CONTENT: dict[TrainingStage, dict[str, object]] = {
    "junior": {
        "title": "初中核心素养培训",
        "summary": "先用课程标准口径把 9 个初中核心素养的边界理清，再抓住每类题真正依赖的关键动作进行判断，通过后方可领取初中标注题。",
        "competencies": [
            {
                "code": "abstraction",
                "name": "抽象能力",
                "definition": "从具体情境中抽取数量关系、图形特征和一般规律，形成可用数学语言表达的问题结构。",
                "focus_tip": "看到“把实际对象转成式子、关系或规则”时，要优先考虑抽象能力。",
                "positive_cues": ["从文字或特例中提炼变量、对象、本质属性", "判断无理数、倒数、绝对值等概念本质", "形成一般表达或数学关系"],
                "negative_cues": ["题目已给出模型，只需计算或读图", "完整列方程并求解现实问题更偏模型观念", "封闭式找规律通常更偏推理能力"],
                "level_guidance": ["L1：识别或提取一个基础数学对象/属性", "L2：从复杂情境中组织多个关系", "L3：形成较完整的一般结构或高水平概括"],
                "boundary_examples": ["无理数个数判断优先抽象能力", "行程列方程中抽象通常只是模型观念的前置支撑"],
            },
            {
                "code": "operation",
                "name": "运算能力",
                "definition": "依据法则和算理选择合适的运算路径，完成变形、推算、求值或检验。",
                "focus_tip": "如果题目的关键在算式处理、代数运算或结果推演，通常与运算能力关联更强。",
                "positive_cues": ["数值计算、代数式化简、求值、因式分解", "解方程、不等式、分式或根式条件", "面积、角度、概率等计算是主推进动作"],
                "negative_cues": ["计算只是证明、读图、建模后的收尾", "只有 180° 或坐标符号但不需要计算", "公式识别服务于证明时优先看推理"],
                "level_guidance": ["L1：单一规则或少量基础计算", "L2：多个运算法则组合使用", "L3：复杂代数结构、参数或综合函数运算主导解题"],
                "boundary_examples": ["整式运算与因式分解标运算 L2，不额外标推理", "分式有意义是代数条件处理，通常标运算 L1"],
            },
            {
                "code": "geometric_intuition",
                "name": "几何直观",
                "definition": "借助图形、图像和位置关系理解数量关系与变化特征，用图帮助分析和求解。",
                "focus_tip": "重点看是否依赖“看图想性质、借图助解”。",
                "positive_cues": ["读几何图、函数图像、坐标图、方格图", "由图形位置关系判断角、边、面积、相似、平行", "用图像上下关系解方程或不等式"],
                "negative_cues": ["只是出现几何名词但没有读图任务", "只用几何公式直接计算", "立体展开或三维想象更偏空间观念"],
                "level_guidance": ["L1：图是找关系的入口", "L2：图形结构是解题主路径", "L3：复杂图形变换或多结构综合主导解题"],
                "boundary_examples": ["函数图像判断不等式解集标几何直观 L2", "三角形三边关系无图时不因几何名词标几何直观"],
            },
            {
                "code": "spatial_conception",
                "name": "空间观念",
                "definition": "认识图形的形状、大小、方位和变换关系，形成对空间结构的想象与表征。",
                "focus_tip": "如果题目强调立体展开、旋转、平移或方位结构，更偏向空间观念。",
                "positive_cues": ["立体图形、三视图、展开图、折叠还原", "空间方位、旋转、翻折后的关系", "由平面图想象空间物体"],
                "negative_cues": ["普通平面几何图、坐标平面图、方格图", "平面折叠只分析角边关系时通常看几何直观/推理", "点在平面坐标系移动不等于空间观念"],
                "level_guidance": ["L1：基础空间形状或方位识别", "L2：展开、折叠、视图之间的转换", "L3：复杂空间结构的综合想象与表达"],
                "boundary_examples": ["方格作图题属于平面图形分析，不标空间观念", "赵爽弦图是平面面积关系，不标空间观念"],
            },
            {
                "code": "reasoning",
                "name": "推理能力",
                "definition": "从条件、性质或结论关系出发，进行合乎逻辑的分析、判断和论证。",
                "focus_tip": "出现证明、说理、由条件推出结论时，要重点关注推理能力。",
                "positive_cues": ["证明、补全证明、平行线判定、全等相似论证", "由条件推出角、边、取值范围或结论", "找规律、递推、归纳到一般项"],
                "negative_cues": ["定义直接套用", "按公式计算或化简", "只识别概念但没有条件到结论链条"],
                "level_guidance": ["L1：一步或两步直接推断", "L2：多步证明、复杂图形关系或递推规律", "L3：复杂综合论证或高水平推理组织"],
                "boundary_examples": ["三边关系推出整数边长标推理 L1", "坐标递推规律可标推理 L2，但封闭规律不等于创新意识"],
            },
            {
                "code": "data_consciousness",
                "name": "数据观念",
                "definition": "理解数据的意义与随机现象的特点，会根据问题整理、描述并解释数据。",
                "focus_tip": "统计图表、频数、概率直观判断等通常与数据观念相关。",
                "positive_cues": ["调查方式、样本与总体", "条形图、扇形图、折线图、频数分布图", "平均数、方差、中位数、众数及样本估计"],
                "negative_cues": ["函数图像、行程图像不是统计数据", "表格只是计费规则时更偏模型观念", "只做普通数值计算不涉及统计意义"],
                "level_guidance": ["L1：识别调查方式、统计图类型或简单统计量", "L2：补全图表、分析数据并估计总体", "L3：复杂数据推断或评价"],
                "boundary_examples": ["作息条形图读图计算标数据观念", "距离-时间图像是函数图像，不标数据观念"],
            },
            {
                "code": "model_consciousness",
                "name": "模型观念",
                "definition": "从现实情境中抽象出数学关系，建立模型并回到情境中解释结果。",
                "focus_tip": "如果题目关键是“建模再求解”，比单纯应用公式更偏向模型观念。",
                "positive_cues": ["行程、工程、收费、利润等现实关系建模", "分段函数、分段计费、规则转方程/函数", "古代应用题列方程组"],
                "negative_cues": ["已经给出解析式只判断图像性质", "统计图表分析优先数据观念", "纯代数运算没有现实关系建模"],
                "level_guidance": ["L1：建立基础方程或数量关系", "L2：分段、方程组或几何现实模型较完整", "L3：复杂情境建模、检验和解释"],
                "boundary_examples": ["阶梯水价表是计费模型，不是统计数据", "现实情境只作包装时不能自动标模型观念"],
            },
            {
                "code": "application_awareness",
                "name": "应用意识",
                "definition": "有意识地把数学概念、原理和方法用于解释现象、分析并解决实际问题。",
                "focus_tip": "侧重“会不会把数学用起来”，不一定要求完整建模。",
                "positive_cues": ["用数学结果比较现实方案", "解释现实规律、风险、效率或公平", "把计算结果返回现实语境判断合理性"],
                "negative_cues": ["只有生活背景但核心是计算、读图、证明或建模", "没有评价、解释、选择或现实意义判断", "建立方程/函数关系优先模型观念"],
                "level_guidance": ["L1：基础现实解释或选择", "L2：多条件现实方案比较", "L3：开放现实任务中的综合评价"],
                "boundary_examples": ["行程图像题是读图还原数量关系，不标应用意识", "路牌距离题是建几何模型，不因交通背景标应用意识"],
            },
            {
                "code": "innovation_awareness",
                "name": "创新意识",
                "definition": "能发现并提出有意义的问题，尝试不同路径、形成新思路并持续优化。",
                "focus_tip": "多解、变式、策略创新或开放探索题通常更容易体现创新意识。",
                "positive_cues": ["开放题、一题多解、方案设计", "先猜想再验证且路径不固定", "提出问题、改造条件、探索多种可能"],
                "negative_cues": ["封闭式找规律且目标唯一", "难题或综合题但仍按标准逻辑推进", "只是求第 n 项且规律充分"],
                "level_guidance": ["L1：有限开放或多路径尝试", "L2：较完整的猜想、验证或方案设计", "L3：高水平开放探索和优化"],
                "boundary_examples": ["坐标递推规律目标封闭，不标创新意识", "复杂几何题难度高不等于创新意识"],
            },
        ],
    },
    "senior": {
        "title": "高中核心素养培训",
        "summary": "先按课程标准理解 6 个高中核心素养的边界，再判断题目真正依赖的是抽象、推理、建模、直观、运算还是数据分析，通过后方可领取高中标注题。",
        "competencies": [
            {
                "code": "mathematical_abstraction",
                "name": "数学抽象",
                "definition": "从数量关系与空间形式中提炼对象、关系和结构，形成符号化的数学表达。",
                "focus_tip": "若核心在概念抽取、关系概括和符号表示，可优先判为数学抽象。",
            },
            {
                "code": "logical_reasoning",
                "name": "逻辑推理",
                "definition": "从事实、定义、性质和条件出发，进行演绎、归纳或类比，形成严谨结论。",
                "focus_tip": "证明、论证、条件推导与结论验证都应重点考虑逻辑推理。",
            },
            {
                "code": "mathematical_modeling",
                "name": "数学建模",
                "definition": "把现实问题抽象为数学模型，经过求解后再回到原情境解释和检验结果。",
                "focus_tip": "看到“情境抽象为函数、方程、概率模型”等过程时，通常涉及数学建模。",
            },
            {
                "code": "intuitive_imagination",
                "name": "直观想象",
                "definition": "借助图形、图像和空间表征理解结构关系、变化趋势与几何性质，建立形与数的联系。",
                "focus_tip": "函数图像、解析几何构型、空间图形判断往往与直观想象强相关。",
            },
            {
                "code": "mathematical_operation",
                "name": "数学运算",
                "definition": "在明确运算对象的基础上选择合适路径，准确完成化简、变形、求值和求解。",
                "focus_tip": "公式变形、代数运算、三角恒等变换等通常首先体现数学运算。",
            },
            {
                "code": "data_analysis",
                "name": "数据分析",
                "definition": "获取并整理数据，进行分析、推断和解释，形成对研究对象特征的认识。",
                "focus_tip": "统计推断、数据比较、概率解释等情境更偏向数据分析。",
            },
        ],
    },
}

STAGE_COMPETENCY_CODES = {
    stage: [item["code"] for item in content["competencies"]]  # type: ignore[index]
    for stage, content in TRAINING_CONTENT.items()
}


def training_scope_allows_stage(training_scope: str, stage: str | None) -> bool:
    if stage is None:
        return False
    if training_scope == "both":
        return stage in {"junior", "senior"}
    return training_scope == stage


def merge_training_scope(current_scope: str, stage: TrainingStage) -> str:
    if current_scope in {"both", stage}:
        return current_scope
    if current_scope == "none":
        return stage
    return "both"


class TrainingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_status(self, user_id: int) -> TrainingStatusResponse:
        user = self._require_user(user_id)
        return TrainingStatusResponse(
            user_id=user.id,
            training_scope=user.training_scope,
            available_stages=["junior", "senior"],
            junior_completed=training_scope_allows_stage(user.training_scope, "junior"),
            senior_completed=training_scope_allows_stage(user.training_scope, "senior"),
        )

    def get_module(self, user_id: int, stage: TrainingStage) -> TrainingModuleResponse:
        self._require_user(user_id)
        content = TRAINING_CONTENT[stage]
        models = self._build_training_question_models(stage)
        questions = self._serialize_training_questions(models)
        return TrainingModuleResponse(
            stage=stage,
            title=str(content["title"]),
            summary=str(content["summary"]),
            pass_threshold=PASS_THRESHOLD,
            required_question_count=len(questions),
            competency_definitions=[
                TrainingCompetencyDefinition(**item)
                for item in content["competencies"]  # type: ignore[arg-type]
            ],
            guide_examples=self._build_guide_examples(stage, models),
            questions=questions,
        )

    def submit_training(self, payload: TrainingSubmitRequest) -> TrainingSubmitResponse:
        user = self._require_user(payload.user_id)
        module = self._build_training_question_models(payload.stage)
        stage_ids = self._stage_competency_id_set(payload.stage)
        stage_name_map = self._stage_competency_name_map(payload.stage)
        stage_detail_map = self._stage_competency_detail_map(payload.stage)
        answer_map = {item.question_id: item for item in payload.answers}

        question_results: list[TrainingQuestionResult] = []
        aggregate_score = 0.0
        correct_questions = 0

        for question in module:
            answer = answer_map.get(question.question_id)
            predicted_levels = self._competency_level_map(
                answer.competencies if answer else [],
                allowed_competency_ids=stage_ids,
            )
            question_score = self._score_question(question.expected_levels, predicted_levels)
            score_percent = round(question_score * 100, 2)
            if score_percent >= PASS_THRESHOLD:
                correct_questions += 1
            aggregate_score += question_score
            question_results.append(
                TrainingQuestionResult(
                    question_id=question.question_id,
                    score_percent=score_percent,
                    is_passed=score_percent >= PASS_THRESHOLD,
                    expected_competency_names=self._resolve_competency_names(
                        question.expected_levels,
                        stage_name_map,
                    ),
                    predicted_competency_names=self._resolve_competency_names(
                        predicted_levels,
                        stage_name_map,
                    ),
                    competency_results=self._build_competency_results(
                        question_id=question.question_id,
                        expected_levels=question.expected_levels,
                        predicted_levels=predicted_levels,
                        detail_map=stage_detail_map,
                    ),
                )
            )

        overall_percent = round((aggregate_score / max(len(module), 1)) * 100, 2)
        passed = overall_percent >= PASS_THRESHOLD
        attempt_no = self._next_attempt_no(user.id, payload.stage)
        completed_at = datetime.utcnow()

        self.db.add(
            AnnotatorTrainingAttempt(
                user_id=user.id,
                edu_stage=payload.stage,
                attempt_no=attempt_no,
                status="PASSED" if passed else "FAILED",
                score_percent=Decimal(str(overall_percent)),
                pass_threshold=PASS_THRESHOLD,
                total_questions=len(module),
                correct_questions=correct_questions,
                summary_json={
                    "question_results": [item.model_dump() for item in question_results],
                },
                completed_at=completed_at,
            )
        )
        if passed:
            user.training_scope = merge_training_scope(user.training_scope, payload.stage)
        self.db.commit()

        return TrainingSubmitResponse(
            stage=payload.stage,
            passed=passed,
            score_percent=overall_percent,
            pass_threshold=PASS_THRESHOLD,
            training_scope=user.training_scope,
            attempt_no=attempt_no,
            completed_at=completed_at,
            question_results=question_results,
        )

    def list_attempts(self, user_id: int, stage: TrainingStage) -> list[TrainingAttemptResponse]:
        self._require_user(user_id)
        stmt = (
            select(AnnotatorTrainingAttempt)
            .where(
                AnnotatorTrainingAttempt.user_id == user_id,
                AnnotatorTrainingAttempt.edu_stage == stage,
            )
            .order_by(
                AnnotatorTrainingAttempt.attempt_no.desc(),
                AnnotatorTrainingAttempt.completed_at.desc(),
            )
        )
        attempts = list(self.db.scalars(stmt))
        return [self._serialize_attempt(attempt) for attempt in attempts]

    def _serialize_attempt(self, attempt: AnnotatorTrainingAttempt) -> TrainingAttemptResponse:
        summary = attempt.summary_json or {}
        raw_results = summary.get("question_results", [])
        question_results = [
            TrainingQuestionResult.model_validate(item)
            for item in raw_results
            if isinstance(item, dict)
        ]
        return TrainingAttemptResponse(
            stage=attempt.edu_stage,  # type: ignore[arg-type]
            passed=attempt.status == "PASSED",
            score_percent=float(attempt.score_percent),
            pass_threshold=int(attempt.pass_threshold),
            attempt_no=int(attempt.attempt_no),
            completed_at=attempt.completed_at,
            question_results=question_results,
        )

    def _require_user(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        return user

    def _build_training_questions(self, stage: TrainingStage) -> list[TrainingQuestionOut]:
        return self._serialize_training_questions(self._build_training_question_models(stage))

    def _serialize_training_questions(
        self,
        models: list["_TrainingQuestionModel"],
    ) -> list[TrainingQuestionOut]:
        return [
            TrainingQuestionOut(
                question_id=item.question_id,
                stem_text=item.stem_text,
                subject_name=item.subject_name,
                grade_name=item.grade_name,
                question_type_name=item.question_type_name,
                answer_text=item.answer_text,
                solution_text=item.solution_text,
                coach_tip=item.coach_tip,
                review_analysis=item.review_analysis,
            )
            for item in models
        ]

    def _build_training_question_models(self, stage: TrainingStage) -> list["_TrainingQuestionModel"]:
        stage_codes = STAGE_COMPETENCY_CODES[stage]
        if stage == "junior":
            return self._build_junior_reviewed_question_models(stage_codes)

        labels = self._stage_gold_labels(stage)
        selected = self._select_training_labels(labels, stage, stage_codes)
        if len(selected) < len(stage_codes):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{stage} 学段金标题量不足，暂时无法生成培训题集",
            )

        models: list[_TrainingQuestionModel] = []
        for label in selected:
            question = label.question
            if question.content is None:
                continue
            hydrate_question_contents(self.db, [question])
            guidance = self._example_guidance(stage, int(question.id))
            expected_levels = {
                item.competency_id: int(item.level_value)
                for item in label.competencies
                if item.competency and item.competency.code in stage_codes
            }
            competency_codes = {
                item.competency_id: item.competency.code
                for item in label.competencies
                if item.competency and item.competency.code in stage_codes
            }
            models.append(
                _TrainingQuestionModel(
                    question_id=question.id,
                    stem_text=question.content.stem_text,
                    subject_name=question.subject.name,
                    grade_name=question.grade.grade_name if question.grade else None,
                    question_type_name=question.question_type.name if question.question_type else None,
                    answer_text=question.content.answer_text,
                    solution_text=question.content.solution_text,
                    expected_levels=expected_levels,
                    competency_codes=competency_codes,
                    coach_tip=guidance.get("coach_tip"),
                    review_analysis=guidance.get("analysis"),
                )
            )
        return models

    def _build_junior_reviewed_question_models(
        self,
        stage_codes: list[str],
    ) -> list["_TrainingQuestionModel"]:
        stmt = (
            select(QuestionLabelAggregate)
            .join(Question, Question.id == QuestionLabelAggregate.question_id)
            .join(Grade, Grade.id == Question.grade_id)
            .options(
                selectinload(QuestionLabelAggregate.question).selectinload(Question.content),
                selectinload(QuestionLabelAggregate.question).selectinload(Question.subject),
                selectinload(QuestionLabelAggregate.question).selectinload(Question.grade),
                selectinload(QuestionLabelAggregate.question).selectinload(Question.question_type),
                selectinload(QuestionLabelAggregate.competencies).selectinload(
                    QuestionAggregateCompetency.competency
                ),
            )
            .where(
                Grade.edu_stage == "junior",
                QuestionLabelAggregate.question_id.in_(JUNIOR_CALIBRATION_QUESTION_IDS),
            )
        )
        aggregates = {
            int(item.question_id): item
            for item in self.db.scalars(stmt).unique()
            if item.question
            and item.question.content
            and item.question.content.stem_text
            and any(competency.level_value > 0 for competency in item.competencies)
        }
        missing_ids = [
            question_id
            for question_id in JUNIOR_CALIBRATION_QUESTION_IDS
            if question_id not in aggregates
        ]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"初中培训样例题缺少已复核结论：{missing_ids}",
            )

        hydrate_question_contents(
            self.db,
            [aggregate.question for aggregate in aggregates.values() if aggregate.question],
        )

        models: list[_TrainingQuestionModel] = []
        for question_id in JUNIOR_CALIBRATION_QUESTION_IDS:
            aggregate = aggregates[question_id]
            question = aggregate.question
            expected_levels = {
                item.competency_id: int(item.level_value)
                for item in aggregate.competencies
                if item.competency and item.competency.code in stage_codes
            }
            competency_codes = {
                item.competency_id: item.competency.code
                for item in aggregate.competencies
                if item.competency and item.competency.code in stage_codes
            }
            guidance = self._example_guidance("junior", int(question.id))
            models.append(
                _TrainingQuestionModel(
                    question_id=question.id,
                    stem_text=question.content.stem_text,
                    subject_name=question.subject.name,
                    grade_name=question.grade.grade_name if question.grade else None,
                    question_type_name=question.question_type.name if question.question_type else None,
                    answer_text=question.content.answer_text,
                    solution_text=question.content.solution_text,
                    expected_levels=expected_levels,
                    competency_codes=competency_codes,
                    coach_tip=guidance.get("coach_tip"),
                    review_analysis=guidance.get("analysis"),
                )
            )
        return models

    def _build_guide_examples(
        self,
        stage: TrainingStage,
        calibration_models: list["_TrainingQuestionModel"],
    ) -> list[TrainingGuideExampleOut]:
        labels = self._stage_gold_labels(stage)
        calibration_ids = {item.question_id for item in calibration_models}
        by_question_id = {item.question_id: item for item in calibration_models}
        definitions = {
            item["code"]: item  # type: ignore[index]
            for item in TRAINING_CONTENT[stage]["competencies"]  # type: ignore[index]
        }

        example_models: list[_TrainingQuestionModel] = []
        for label in labels:
            question_id = int(label.question_id)
            if question_id in calibration_ids:
                continue
            example = self._training_model_from_label(label, stage)
            if example is not None:
                example_models.append(example)
            if len(example_models) >= 2:
                break

        if len(example_models) < 2:
            for model in calibration_models:
                if model.question_id in {item.question_id for item in example_models}:
                    continue
                example_models.append(by_question_id[model.question_id])
                if len(example_models) >= 2:
                    break

        examples: list[TrainingGuideExampleOut] = []
        target_count = len(JUNIOR_GUIDE_EXAMPLE_IDS) if stage == "junior" else 2
        if stage == "junior":
            ordered_examples = [
                model
                for question_id in JUNIOR_GUIDE_EXAMPLE_IDS
                for model in calibration_models
                if model.question_id == question_id
            ]
            if ordered_examples:
                example_models = ordered_examples
        for model in example_models[:target_count]:
            positive_competencies = []
            for competency_id, level_value in model.expected_levels.items():
                if level_value <= 0:
                    continue
                code = model.competency_codes.get(competency_id)
                definition = definitions.get(code or "")
                if definition is None:
                    continue
                positive_competencies.append(
                    TrainingGuideExampleCompetencyOut(
                        competency_id=competency_id,
                        competency_name=str(definition["name"]),
                        level_value=level_value,
                        definition=str(definition["definition"]),
                        focus_tip=str(definition["focus_tip"]),
                        level_reason=self._level_reason(
                            level_value,
                            question_id=model.question_id,
                            competency_code=code,
                        ),
                    )
                )
            if not positive_competencies:
                continue
            competency_names = "、".join(item.competency_name for item in positive_competencies)
            examples.append(
                TrainingGuideExampleOut(
                    question_id=model.question_id,
                    stem_text=model.stem_text,
                    subject_name=model.subject_name,
                    grade_name=model.grade_name,
                    question_type_name=model.question_type_name,
                    answer_text=model.answer_text,
                    solution_text=model.solution_text,
                    coach_tip=model.coach_tip
                    or f"这道样例重点看 {competency_names}。先判断题目的关键解题动作，再对照素养定义确定层级。",
                    competencies=positive_competencies,
                )
            )
        return examples

    def _training_model_from_label(
        self,
        label: QuestionGoldLabel,
        stage: TrainingStage,
    ) -> "_TrainingQuestionModel | None":
        stage_codes = set(STAGE_COMPETENCY_CODES[stage])
        question = label.question
        if question is None or question.content is None:
            return None
        expected_levels = {
            item.competency_id: int(item.level_value)
            for item in label.competencies
            if item.competency and item.competency.code in stage_codes
        }
        competency_codes = {
            item.competency_id: item.competency.code
            for item in label.competencies
            if item.competency and item.competency.code in stage_codes
        }
        guidance = self._example_guidance(stage, int(question.id))
        return _TrainingQuestionModel(
            question_id=question.id,
            stem_text=question.content.stem_text,
            subject_name=question.subject.name,
            grade_name=question.grade.grade_name if question.grade else None,
            question_type_name=question.question_type.name if question.question_type else None,
            answer_text=question.content.answer_text,
            solution_text=question.content.solution_text,
            expected_levels=expected_levels,
            competency_codes=competency_codes,
            coach_tip=guidance.get("coach_tip"),
            review_analysis=guidance.get("analysis"),
        )

    def _stage_gold_labels(self, stage: TrainingStage) -> list[QuestionGoldLabel]:
        stmt = (
            select(QuestionGoldLabel)
            .join(Question, Question.id == QuestionGoldLabel.question_id)
            .join(Grade, Grade.id == Question.grade_id)
            .options(
                selectinload(QuestionGoldLabel.question).selectinload(Question.content),
                selectinload(QuestionGoldLabel.question).selectinload(Question.subject),
                selectinload(QuestionGoldLabel.question).selectinload(Question.grade),
                selectinload(QuestionGoldLabel.question).selectinload(Question.question_type),
                selectinload(QuestionGoldLabel.competencies).selectinload(QuestionGoldCompetency.competency),
            )
            .where(Grade.edu_stage == stage)
            .order_by(QuestionGoldLabel.question_id.asc(), QuestionGoldLabel.id.asc())
        )
        labels = list(self.db.scalars(stmt).unique())
        return [
            label
            for label in labels
            if label.question
            and label.question.content
            and label.question.content.stem_text
            and any(item.level_value > 0 for item in label.competencies)
        ]

    def _select_training_labels(
        self,
        labels: list[QuestionGoldLabel],
        stage: TrainingStage,
        stage_codes: list[str],
    ) -> list[QuestionGoldLabel]:
        if stage == "junior":
            by_question_id = {int(label.question_id): label for label in labels}
            selected = [
                by_question_id[question_id]
                for question_id in JUNIOR_CALIBRATION_QUESTION_IDS
                if question_id in by_question_id
            ]
            if len(selected) != len(JUNIOR_CALIBRATION_QUESTION_IDS):
                missing_ids = [
                    question_id
                    for question_id in JUNIOR_CALIBRATION_QUESTION_IDS
                    if question_id not in by_question_id
                ]
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"初中培训样例题缺少金标：{missing_ids}",
                )
            return selected

        selected: list[QuestionGoldLabel] = []
        used_question_ids: set[int] = set()

        for code in stage_codes:
            matched = next(
                (
                    label
                    for label in labels
                    if label.question_id not in used_question_ids
                    and any(
                        item.competency
                        and item.competency.code == code
                        and item.level_value > 0
                        for item in label.competencies
                    )
                ),
                None,
            )
            if matched is not None:
                selected.append(matched)
                used_question_ids.add(matched.question_id)

        for label in labels:
            if label.question_id in used_question_ids:
                continue
            selected.append(label)
            used_question_ids.add(label.question_id)
            if len(selected) >= len(stage_codes):
                break

        return selected[: len(stage_codes)]

    def _next_attempt_no(self, user_id: int, stage: TrainingStage) -> int:
        stmt = select(func.max(AnnotatorTrainingAttempt.attempt_no)).where(
            AnnotatorTrainingAttempt.user_id == user_id,
            AnnotatorTrainingAttempt.edu_stage == stage,
        )
        current = self.db.scalar(stmt) or 0
        return int(current) + 1

    def _stage_competency_id_set(self, stage: TrainingStage) -> set[int]:
        rows = self.db.execute(
            select(Competency.id).where(Competency.code.in_(STAGE_COMPETENCY_CODES[stage]))
        ).all()
        return {int(row[0]) for row in rows}

    def _stage_competency_name_map(self, stage: TrainingStage) -> dict[int, str]:
        rows = self.db.execute(
            select(Competency.id, Competency.name).where(Competency.code.in_(STAGE_COMPETENCY_CODES[stage]))
        ).all()
        return {int(row[0]): str(row[1]) for row in rows}

    def _stage_competency_detail_map(self, stage: TrainingStage) -> dict[int, dict[str, str]]:
        content_by_code = {
            str(item["code"]): item
            for item in TRAINING_CONTENT[stage]["competencies"]  # type: ignore[index]
        }
        rows = self.db.execute(
            select(Competency.id, Competency.code, Competency.name).where(
                Competency.code.in_(STAGE_COMPETENCY_CODES[stage])
            )
        ).all()
        details: dict[int, dict[str, str]] = {}
        for competency_id, code, db_name in rows:
            content = content_by_code.get(str(code), {})
            details[int(competency_id)] = {
                "code": str(code),
                "name": str(content.get("name") or db_name),
                "definition": str(content.get("definition") or ""),
                "focus_tip": str(content.get("focus_tip") or ""),
            }
        return details

    def _competency_level_map(
        self,
        items: Iterable,
        *,
        allowed_competency_ids: set[int],
    ) -> dict[int, int]:
        result: dict[int, int] = {}
        for item in items:
            competency_id = int(item.competency_id)
            if competency_id not in allowed_competency_ids:
                continue
            result[competency_id] = int(item.level_value)
        return result

    def _score_question(
        self,
        expected_levels: dict[int, int],
        predicted_levels: dict[int, int],
    ) -> float:
        expected_positive = {cid for cid, level in expected_levels.items() if level > 0}
        predicted_positive = {cid for cid, level in predicted_levels.items() if level > 0}
        intersection = expected_positive & predicted_positive

        if not expected_positive and not predicted_positive:
            presence_f1 = 1.0
        else:
            precision = len(intersection) / len(predicted_positive) if predicted_positive else 0.0
            recall = len(intersection) / len(expected_positive) if expected_positive else 0.0
            presence_f1 = (
                0.0
                if precision + recall == 0
                else (2 * precision * recall) / (precision + recall)
            )

        union_positive = expected_positive | predicted_positive
        if not union_positive:
            level_accuracy = 1.0
        else:
            matches = sum(
                1 for cid in union_positive if predicted_levels.get(cid, 0) == expected_levels.get(cid, 0)
            )
            level_accuracy = matches / len(union_positive)

        return (0.7 * presence_f1) + (0.3 * level_accuracy)

    def _resolve_competency_names(
        self,
        levels: dict[int, int],
        name_map: dict[int, str],
    ) -> list[str]:
        return [name_map[cid] for cid, level in levels.items() if level > 0 and cid in name_map]

    def _build_competency_results(
        self,
        *,
        question_id: int,
        expected_levels: dict[int, int],
        predicted_levels: dict[int, int],
        detail_map: dict[int, dict[str, str]],
    ) -> list[TrainingQuestionCompetencyResult]:
        results: list[TrainingQuestionCompetencyResult] = []
        for competency_id, detail in detail_map.items():
            expected_level = int(expected_levels.get(competency_id, 0))
            selected_level = int(predicted_levels.get(competency_id, 0))
            results.append(
                TrainingQuestionCompetencyResult(
                    competency_id=competency_id,
                    competency_name=detail["name"],
                    expected_level=expected_level,
                    selected_level=selected_level,
                    is_match=expected_level == selected_level,
                    definition=detail["definition"],
                    focus_tip=detail["focus_tip"],
                    level_reason=self._level_reason(
                        expected_level,
                        question_id=question_id,
                        competency_code=detail.get("code"),
                    ),
                )
            )
        return results

    def _example_guidance(self, stage: TrainingStage, question_id: int) -> dict[str, object]:
        if stage != "junior":
            return {}
        return JUNIOR_EXAMPLE_GUIDANCE.get(question_id, {})

    def _level_reason(
        self,
        level_value: int,
        *,
        question_id: int | None = None,
        competency_code: str | None = None,
    ) -> str:
        if question_id is not None and competency_code:
            guidance = JUNIOR_EXAMPLE_GUIDANCE.get(question_id)
            level_reasons = guidance.get("level_reasons") if guidance else None
            if isinstance(level_reasons, dict):
                reason = level_reasons.get(competency_code)
                if isinstance(reason, str):
                    return reason
        if level_value <= 0:
            return "该素养基本不参与本题求解，通常不需要单独标出。"
        if level_value == 1:
            return "该素养有体现，但主要用于辅助理解、读图或局部步骤，属于弱体现。"
        if level_value == 2:
            return "该素养支撑了关键求解过程，对完成题目有明显作用，属于中等体现。"
        return "该素养主导整题的理解、转化或求解路径，是核心素养，属于强体现。"


class _TrainingQuestionModel:
    def __init__(
        self,
        *,
        question_id: int,
        stem_text: str,
        subject_name: str,
        grade_name: str | None,
        question_type_name: str | None,
        answer_text: str | None,
        solution_text: str | None,
        expected_levels: dict[int, int],
        competency_codes: dict[int, str] | None = None,
        coach_tip: str | None = None,
        review_analysis: str | None = None,
    ) -> None:
        self.question_id = question_id
        self.stem_text = stem_text
        self.subject_name = subject_name
        self.grade_name = grade_name
        self.question_type_name = question_type_name
        self.answer_text = answer_text
        self.solution_text = solution_text
        self.expected_levels = expected_levels
        self.competency_codes = competency_codes or {}
        self.coach_tip = coach_tip
        self.review_analysis = review_analysis
