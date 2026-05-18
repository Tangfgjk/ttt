from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SystemConfigEntry(TimestampMixin, Base):
    __tablename__ = "system_config_entries"

    config_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
