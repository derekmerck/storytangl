from __future__ import annotations

from enum import Enum
import re
from typing import Any, Iterable


def get_tag_values(
    tags: Iterable[Any],
    *,
    prefix: str | None = None,
    value_type: type | None = None,
) -> set[Any]:
    """Parse tag values with optional ``prefix:value`` extraction and coercion."""
    if prefix is None and value_type is None:
        raise TypeError("Expected at least one of: prefix, value_type")
    if prefix is None and value_type in (str, int):
        raise TypeError("prefix is required when value_type is str or int")

    target_type: type = value_type or str
    regex = None
    if prefix is not None:
        regex = re.compile(rf"^{re.escape(prefix)}\W(.*)$")

    result: set[Any] = set()
    for tag in tags:
        if regex is not None and isinstance(tag, str):
            match = regex.match(tag)
            if not match:
                continue
            raw: object = match.group(1)
        else:
            raw = tag

        if value_type is None:
            if isinstance(raw, str):
                result.add(raw)
            continue

        if issubclass(target_type, Enum):
            try:
                result.add(target_type(raw))
            except (ValueError, TypeError):
                continue
        elif target_type is int:
            try:
                result.add(int(raw))
            except (ValueError, TypeError):
                continue
        elif target_type is str:
            if isinstance(raw, str):
                result.add(raw)
        else:
            try:
                result.add(target_type(raw))
            except Exception:
                continue

    return result
