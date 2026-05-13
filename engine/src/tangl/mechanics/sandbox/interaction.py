"""Sponsored interaction declarations for sandbox concepts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from pydantic import BaseModel, Field

from tangl.core.runtime_op import Effect, Predicate

RuntimeOpT = TypeVar("RuntimeOpT", Predicate, Effect)


def normalize_runtime_ops(value: object, op_kind: type[RuntimeOpT]) -> list[RuntimeOpT]:
    """Normalize compact predicate/effect authoring values."""
    if value is None:
        return []
    if isinstance(value, op_kind):
        return [value]
    if isinstance(value, str):
        return [op_kind(expr=value)]
    if isinstance(value, dict):
        return [op_kind.model_validate(value)]
    if not isinstance(value, Iterable):
        raise TypeError(f"Expected {op_kind.__name__} expression, got {type(value)!r}")
    out: list[RuntimeOpT] = []
    for item in value:
        if isinstance(item, op_kind):
            out.append(item)
        elif isinstance(item, str):
            out.append(op_kind(expr=item))
        elif isinstance(item, dict):
            out.append(op_kind.model_validate(item))
        else:
            raise TypeError(f"Expected {op_kind.__name__} expression, got {type(item)!r}")
    return out


class SandboxInteraction(BaseModel):
    """Ordinary action sponsored by a scoped sandbox concept."""

    label: str
    text: str
    target: str
    journal_text: str = ""
    activation: str | None = None
    once: bool = False
    return_to_location: bool = False
    availability: list[Predicate] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
