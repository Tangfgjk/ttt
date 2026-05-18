from __future__ import annotations

from app.core.time_utils import utc_iso_timestamp
from app.models.system import SystemConfigEntry

ANNOTATION_POLICY_CONFIG_KEY = "annotation_policy"
DEFAULT_ANNOTATOR_COUNT = 3
ALLOWED_ANNOTATOR_COUNTS = {1, 2, 3}
SYNC_STATUS_VALUES = {"idle", "running", "completed", "failed"}


class AnnotationPolicyStore:
    def __init__(self, db) -> None:
        self.db = db

    def get_annotator_count(self) -> int:
        entry = self.db.get(SystemConfigEntry, ANNOTATION_POLICY_CONFIG_KEY)
        if entry is None:
            return DEFAULT_ANNOTATOR_COUNT
        value = entry.value_json.get("annotator_count")
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return DEFAULT_ANNOTATOR_COUNT
        return normalized if normalized in ALLOWED_ANNOTATOR_COUNTS else DEFAULT_ANNOTATOR_COUNT

    def set_annotator_count(self, annotator_count: int) -> None:
        normalized = int(annotator_count)
        if normalized not in ALLOWED_ANNOTATOR_COUNTS:
            raise ValueError(f"Unsupported annotator count: {annotator_count}")

        entry = self.db.get(SystemConfigEntry, ANNOTATION_POLICY_CONFIG_KEY)
        if entry is None:
            entry = SystemConfigEntry(
                config_key=ANNOTATION_POLICY_CONFIG_KEY,
                value_json={"annotator_count": normalized},
            )
            self.db.add(entry)
            return

        entry.value_json = {**(entry.value_json or {}), "annotator_count": normalized}

    def get_sync_status(self) -> dict:
        entry = self.db.get(SystemConfigEntry, ANNOTATION_POLICY_CONFIG_KEY)
        if entry is None:
            return {
                "status": "idle",
                "target_annotator_count": DEFAULT_ANNOTATOR_COUNT,
                "affected_question_count": 0,
                "updated_question_count": 0,
                "started_at": None,
                "finished_at": None,
                "error_message": None,
            }
        value = entry.value_json or {}
        sync = value.get("sync_status") or {}
        status = sync.get("status")
        normalized_status = status if status in SYNC_STATUS_VALUES else "idle"
        return {
            "status": normalized_status,
            "target_annotator_count": self._normalize_annotator_count(
                sync.get("target_annotator_count"),
                fallback=self.get_annotator_count(),
            ),
            "affected_question_count": self._normalize_non_negative_int(
                sync.get("affected_question_count")
            ),
            "updated_question_count": self._normalize_non_negative_int(
                sync.get("updated_question_count")
            ),
            "started_at": sync.get("started_at"),
            "finished_at": sync.get("finished_at"),
            "error_message": sync.get("error_message"),
        }

    def set_sync_status(
        self,
        *,
        status: str,
        target_annotator_count: int,
        affected_question_count: int,
        updated_question_count: int = 0,
        started_at: str | None = None,
        finished_at: str | None = None,
        error_message: str | None = None,
    ) -> None:
        normalized_status = status if status in SYNC_STATUS_VALUES else "idle"
        payload = {
            "status": normalized_status,
            "target_annotator_count": self._normalize_annotator_count(target_annotator_count),
            "affected_question_count": self._normalize_non_negative_int(affected_question_count),
            "updated_question_count": self._normalize_non_negative_int(updated_question_count),
            "started_at": started_at,
            "finished_at": finished_at,
            "error_message": error_message,
        }
        entry = self.db.get(SystemConfigEntry, ANNOTATION_POLICY_CONFIG_KEY)
        if entry is None:
            entry = SystemConfigEntry(
                config_key=ANNOTATION_POLICY_CONFIG_KEY,
                value_json={
                    "annotator_count": self._normalize_annotator_count(target_annotator_count),
                    "sync_status": payload,
                },
            )
            self.db.add(entry)
            return

        entry.value_json = {**(entry.value_json or {}), "sync_status": payload}

    @staticmethod
    def timestamp_now() -> str:
        return utc_iso_timestamp()

    def _normalize_annotator_count(self, value: object, fallback: int = DEFAULT_ANNOTATOR_COUNT) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return fallback
        return normalized if normalized in ALLOWED_ANNOTATOR_COUNTS else fallback

    @staticmethod
    def _normalize_non_negative_int(value: object) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError):
            return 0
        return max(normalized, 0)


def describe_annotation_policy(annotator_count: int) -> str:
    if annotator_count <= 1:
        return "单人标注即定稿，不进入复核。"
    if annotator_count == 2:
        return "双人独立标注，一致则直接完成，不一致进入复核。"
    return "三人独立标注，按多数聚合；存在争议时进入复核。"
