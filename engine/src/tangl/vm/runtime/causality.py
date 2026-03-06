"""Causality tracking for debug/preview traversal sessions."""

from __future__ import annotations

from enum import Enum


class CausalityMode(str, Enum):
    """Session causality fidelity state."""

    CLEAN = "clean"
    SOFT_DIRTY = "soft_dirty"
    HARD_DIRTY = "hard_dirty"


__all__ = ["CausalityMode"]
