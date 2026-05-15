from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.assessment import (
    AnnotatorTrainingAttempt,
    QuestionGoldCompetency,
    QuestionGoldLabel,
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
            },
            {
                "code": "operation",
                "name": "运算能力",
                "definition": "依据法则和算理选择合适的运算路径，完成变形、推算、求值或检验。",
                "focus_tip": "如果题目的关键在算式处理、代数运算或结果推演，通常与运算能力关联更强。",
            },
            {
                "code": "geometric_intuition",
                "name": "几何直观",
                "definition": "借助图形、图像和位置关系理解数量关系与变化特征，用图帮助分析和求解。",
                "focus_tip": "重点看是否依赖“看图想性质、借图助解”。",
            },
            {
                "code": "spatial_conception",
                "name": "空间观念",
                "definition": "认识图形的形状、大小、方位和变换关系，形成对空间结构的想象与表征。",
                "focus_tip": "如果题目强调立体展开、旋转、平移或方位结构，更偏向空间观念。",
            },
            {
                "code": "reasoning",
                "name": "推理能力",
                "definition": "从条件、性质或结论关系出发，进行合乎逻辑的分析、判断和论证。",
                "focus_tip": "出现证明、说理、由条件推出结论时，要重点关注推理能力。",
            },
            {
                "code": "data_consciousness",
                "name": "数据观念",
                "definition": "理解数据的意义与随机现象的特点，会根据问题整理、描述并解释数据。",
                "focus_tip": "统计图表、频数、概率直观判断等通常与数据观念相关。",
            },
            {
                "code": "model_consciousness",
                "name": "模型观念",
                "definition": "从现实情境中抽象出数学关系，建立模型并回到情境中解释结果。",
                "focus_tip": "如果题目关键是“建模再求解”，比单纯应用公式更偏向模型观念。",
            },
            {
                "code": "application_awareness",
                "name": "应用意识",
                "definition": "有意识地把数学概念、原理和方法用于解释现象、分析并解决实际问题。",
                "focus_tip": "侧重“会不会把数学用起来”，不一定要求完整建模。",
            },
            {
                "code": "innovation_awareness",
                "name": "创新意识",
                "definition": "能发现并提出有意义的问题，尝试不同路径、形成新思路并持续优化。",
                "focus_tip": "多解、变式、策略创新或开放探索题通常更容易体现创新意识。",
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
            )
            for item in models
        ]

    def _build_training_question_models(self, stage: TrainingStage) -> list["_TrainingQuestionModel"]:
        stage_codes = STAGE_COMPETENCY_CODES[stage]
        labels = self._stage_gold_labels(stage)
        selected = self._select_training_labels(labels, stage_codes)
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
        for model in example_models[:2]:
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
                        level_reason=self._level_reason(level_value),
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
                    coach_tip=f"这道样例重点看 {competency_names}。先判断题目的关键解题动作，再对照素养定义确定层级。",
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
        stage_codes: list[str],
    ) -> list[QuestionGoldLabel]:
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
                    level_reason=self._level_reason(expected_level),
                )
            )
        return results

    def _level_reason(self, level_value: int) -> str:
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
