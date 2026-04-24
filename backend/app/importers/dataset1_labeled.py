from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from app.importers.base import BaseImporter, ImporterError

COMPETENCY_HEADERS = [
    "抽象能力",
    "运算能力",
    "几何直观",
    "空间观念",
    "推理能力",
    "数据观念",
    "模型观念",
    "应用意识",
    "创新意识",
]
COGNITIVE_HEADERS = ["识记", "理解", "应用", "分析", "综合", "评价"]


class Dataset1LabeledImporter(BaseImporter):
    record_type = "question"

    def parse(self, file_path: Path) -> list[dict]:
        if not file_path.exists():
            raise ImporterError(f"File not found: {file_path}")

        workbook = load_workbook(file_path, read_only=True, data_only=True)
        sheet = workbook[workbook.sheetnames[0]]
        rows = list(sheet.iter_rows(values_only=True))
        if len(rows) < 3:
            raise ImporterError("Dataset1 workbook does not contain expected header rows.")

        header_row_1 = list(rows[0])
        header_row_2 = list(rows[1])
        merged_headers: list[str | None] = []
        current = None
        for part1, part2 in zip(header_row_1, header_row_2, strict=False):
            if part1 is not None:
                current = part1
            merged_headers.append(part2 if part2 is not None else current)

        records: list[dict] = []
        for row in rows[2:]:
            if not row or row[0] is None:
                continue

            payload = dict(zip(merged_headers, row, strict=False))
            competencies = {
                header: int(payload.get(header) or 0)
                for header in COMPETENCY_HEADERS
                if payload.get(header) is not None
            }
            cognitive_levels = {
                header: int(payload.get(header) or 0)
                for header in COGNITIVE_HEADERS
                if payload.get(header) is not None
            }
            records.append(
                {
                    "source_record_key": str(payload["初中题目id"]),
                    "raw_payload": {
                        "question_id": payload["初中题目id"],
                        "question_text": payload["试题内容"],
                        "knowledge_text": payload["知识点"],
                        "cognitive_levels": cognitive_levels,
                        "competencies": competencies,
                    },
                }
            )

        return records
