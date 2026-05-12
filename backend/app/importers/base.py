from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from pathlib import Path


class ImporterError(RuntimeError):
    """Raised when a source file cannot be parsed into importable records."""


class BaseImporter(ABC):
    """Base importer for local files.

    The first version of the import module focuses on storing raw source
    records into `source_question_records`. Normalization into business tables
    will be added in the next iteration.
    """

    record_type: str = "question"

    @abstractmethod
    def parse(self, file_path: Path) -> list[dict]:
        """Parse a file and return raw source records ready for persistence."""


def make_json_safe(value):
    """Convert importer payloads into values that can be stored in JSON columns."""

    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value
