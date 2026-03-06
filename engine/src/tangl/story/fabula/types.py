from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Protocol, runtime_checkable
from uuid import UUID


class InitMode(str, Enum):
    """Graph initialization modes for story38."""

    LAZY = "lazy"
    EAGER = "eager"


@runtime_checkable
class WorldDomainFacet(Protocol):
    """Lightweight domain facet contract for world-level authorities."""

    def get_authorities(self) -> Iterable[object]: ...


@runtime_checkable
class WorldTemplatesFacet(Protocol):
    """Lightweight templates facet contract for provisioning scope groups."""

    def get_template_scope_groups(self, *, caller: Any = None, graph: Any = None) -> Iterable[Iterable[Any]]: ...


@runtime_checkable
class WorldAssetsFacet(Protocol):
    """Lightweight assets facet contract (token/platonic factories)."""


@runtime_checkable
class WorldResourcesFacet(Protocol):
    """Lightweight resources facet contract (media/data inventories)."""


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
    """Raised when EAGER initialization cannot satisfy hard requirements."""

    def __init__(self, report: InitReport):
        self.report = report
        super().__init__(
            "EAGER initialization failed: "
            f"{len(report.unresolved_hard)} unresolved hard dependencies"
        )


class ResolutionFailureReason(str, Enum):
    """Typed failure reasons for LAZY destination wiring checks."""

    NO_TEMPLATE = "no_template"
    AMBIGUOUS_TEMPLATE = "ambiguous_template"


class ResolutionError(RuntimeError):
    """Raised when LAZY destination wiring cannot resolve canonical targets."""

    def __init__(
        self,
        *,
        source_node_id: UUID | None,
        source_node_label: str | None,
        action_id: UUID | None,
        action_label: str | None,
        authored_ref: str | None,
        canonical_ref: str | None,
        reason: ResolutionFailureReason,
        selector: dict[str, Any],
        world_id: str | None = None,
        bundle_id: str | None = None,
    ) -> None:
        self.source_node_id = source_node_id
        self.source_node_label = source_node_label
        self.action_id = action_id
        self.action_label = action_label
        self.authored_ref = authored_ref
        self.canonical_ref = canonical_ref
        self.reason = reason
        self.selector = selector
        self.world_id = world_id
        self.bundle_id = bundle_id
        super().__init__(
            f"LAZY destination resolution failed ({reason.value}): "
            f"action={action_label or action_id}, source={source_node_label or source_node_id}, "
            f"authored_ref={authored_ref!r}, canonical_ref={canonical_ref!r}"
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
