"""Shared enum helpers for SQLAlchemy models."""

import enum as py_enum


class StrEnum(str, py_enum.Enum):
    """Enum that stringifies to its value for DB compatibility."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
