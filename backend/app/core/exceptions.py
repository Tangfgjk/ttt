from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DomainError(Exception):
    """Base domain exception for application-level business failures."""

    message: str

    def __str__(self) -> str:
        return self.message
