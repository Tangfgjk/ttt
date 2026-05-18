from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def local_day_start_utc_naive() -> datetime:
    local_now = datetime.now(ASIA_SHANGHAI)
    local_day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_day_start.astimezone(timezone.utc).replace(tzinfo=None)
