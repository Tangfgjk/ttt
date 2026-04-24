from __future__ import annotations

import json
from pathlib import Path

from app.importers.base import BaseImporter, ImporterError


class Dataset2QuestionJsonImporter(BaseImporter):
    record_type = "question"

    def parse(self, file_path: Path) -> list[dict]:
        if not file_path.exists():
            raise ImporterError(f"File not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        items = payload if isinstance(payload, list) else [payload]
        records: list[dict] = []

        for item in items:
            source_key = item.get("exerciseID")
            if not source_key:
                raise ImporterError("Dataset2 JSON record is missing exerciseID.")
            records.append(
                {
                    "source_record_key": str(source_key),
                    "raw_payload": item,
                }
            )

        return records
