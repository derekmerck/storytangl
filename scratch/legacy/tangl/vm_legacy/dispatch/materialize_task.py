"""Materialization dispatch task and phases."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class MaterializeTask(StrEnum):
    """Task identifiers for template materialization dispatch."""

    MATERIALIZE = "fabula.materialize"


class MaterializePhase(IntEnum):
    """Priority levels within the materialization dispatch pipeline."""

    EARLY = 10
    NORMAL = 50
    LATE = 80
    LAST = 90
