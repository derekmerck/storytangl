"""Internal user-field coercion helpers for the service manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any


_TRUE_STRINGS = {"1", "true", "t", "yes", "y", "on"}
_FALSE_STRINGS = {"0", "false", "f", "no", "n", "off", ""}


def parse_bool_flag(value: Any, *, field_name: str) -> bool:
    """Parse one boolean-like transport value."""

    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
    raise ValueError(f"{field_name} must be a boolean-like value")


def parse_datetime_field(value: Any, *, field_name: str) -> datetime | None:
    """Parse one optional ISO datetime transport value."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO datetime string") from exc
    raise ValueError(f"{field_name} must be a datetime or ISO datetime string")


__all__ = ["parse_bool_flag", "parse_datetime_field"]
