from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID


class InitMode(str, Enum):
    """Graph initialization modes for story38."""

    MINIMAL = "minimal"
    FULLY_SPECIFIED = "fully_specified"


@dataclass(slots=True)
class UnresolvedDependency:
    """Diagnostic payload for an unresolved dependency edge."""

    dependency_id: UUID
    source_id: UUID | None
    label: str | None
    identifier: str | None
    hard_requirement: bool


@dataclass(slots=True)
class InitReport:
    """Structured diagnostics emitted during story graph initialization."""

    mode: InitMode
    materialized_counts: dict[str, int] = field(default_factory=dict)
    prelinked_counts: dict[str, int] = field(default_factory=dict)
    unresolved_hard: list[UnresolvedDependency] = field(default_factory=list)
    unresolved_soft: list[UnresolvedDependency] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def bump_materialized(self, key: str, amount: int = 1) -> None:
        self.materialized_counts[key] = self.materialized_counts.get(key, 0) + amount

    def bump_prelinked(self, key: str, amount: int = 1) -> None:
        self.prelinked_counts[key] = self.prelinked_counts.get(key, 0) + amount


class GraphInitializationError(RuntimeError):
    """Raised when fully specified initialization cannot satisfy hard requirements."""

    def __init__(self, report: InitReport):
        self.report = report
        super().__init__(
            "Fully specified initialization failed: "
            f"{len(report.unresolved_hard)} unresolved hard dependencies"
        )


@dataclass(slots=True)
class StoryInitResult:
    """Result of creating a story graph from a story38 world."""

    graph: Any
    report: InitReport
    entry_ids: list[UUID]
    source_map: dict[str, Any] = field(default_factory=dict)
    codec_state: dict[str, Any] = field(default_factory=dict)
    codec_id: str | None = None
