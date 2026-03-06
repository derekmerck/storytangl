"""Compatibility frame exports for legacy import paths."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .runtime.frame import Frame
from .traversable import TraversableEdge as ChoiceEdge


@dataclass
class StackFrame:
    """Minimal stack-frame record retained for legacy tests/importers."""

    edge: Any
    return_phase: Any


__all__ = ["ChoiceEdge", "Frame", "StackFrame"]
