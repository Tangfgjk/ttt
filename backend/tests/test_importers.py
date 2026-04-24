from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from app.importers.base import make_json_safe
from app.importers.dataset1_labeled import Dataset1LabeledImporter
from app.importers.dataset2_question_json import Dataset2QuestionJsonImporter


def test_dataset2_question_json_importer(tmp_path: Path) -> None:
    file_path = tmp_path / "question.json"
    payload = {
        "exerciseID": "Q_JSON_001",
        "question": "示例题目",
        "subjectCategory": "math",
    }
    file_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    importer = Dataset2QuestionJsonImporter()
    records = importer.parse(file_path)

    assert len(records) == 1
    assert records[0]["source_record_key"] == "Q_JSON_001"
    assert records[0]["raw_payload"]["question"] == "示例题目"


def test_dataset1_labeled_importer(tmp_path: Path) -> None:
    file_path = tmp_path / "dataset1.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["初中题目id", "试题内容", "知识点", "认知层级水平", None, "核心素养", None])
    sheet.append([None, None, None, "识记", "理解", "抽象能力", "运算能力"])
    sheet.append(["Q_1001", "题目内容", "倒数", 1, None, 1, None])
    workbook.save(file_path)

    importer = Dataset1LabeledImporter()
    records = importer.parse(file_path)

    assert len(records) == 1
    assert records[0]["source_record_key"] == "Q_1001"
    assert records[0]["raw_payload"]["knowledge_text"] == "倒数"
    assert records[0]["raw_payload"]["cognitive_levels"]["识记"] == 1


def test_make_json_safe_serializes_datetime() -> None:
    payload = {"tested_at": datetime(2026, 4, 24, 21, 0, 0)}
    converted = make_json_safe(payload)
    assert converted["tested_at"] == "2026-04-24T21:00:00"
