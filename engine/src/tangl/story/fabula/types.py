from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, TypeAlias
from uuid import UUID


JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


class InitMode(str, Enum):
    """Initialization depth for story graph materialization."""

    LAZY = "lazy"
    EAGER = "eager"


@dataclass(slots=True)
class AuthoredRef:
    """Best-effort authored provenance for compile diagnostics.

    Notes
    -----
    This surface intentionally stays coarse in v1. File-level provenance plus
    compiler-known authored paths are sufficient for bundle preflight without
    blocking on line/column mapping.
    """

    path: str | None = None
    story_key: str | None = None
    authored_path: str | None = None
    label: str | None = None
    note: str | None = None


class CompileSeverity(str, Enum):
    """Severity for compile diagnostics.

    Notes
    -----
    v1 of compiler diagnostics emits only ``error`` issues. ``warning`` exists
    so the surface can align with later authoring-integrity diagnostics work.
    """

    ERROR = "error"
    WARNING = "warning"


@dataclass(slots=True)
class CompileIssue:
    """Structured compiler diagnostic stored on a compiled story bundle.

    Notes
    -----
    ``details`` is reserved for JSON-like payloads only. The compiler module
    documents allowed keys per issue code near its diagnostics helpers.
    """

    code: str
    severity: CompileSeverity
    message: str
    phase: Literal["compile"] = "compile"
    subject_label: str | None = None
    source_ref: AuthoredRef | None = None
    related_identifiers: list[str] = field(default_factory=list)
    details: dict[str, JsonValue] = field(default_factory=dict)

@dataclass(slots=True)
class UnresolvedDependency:
    """Structured diagnostic record for an unresolved dependency edge."""

    dependency_id: UUID
    source_id: UUID | None
    label: str | None
    identifier: str | None
    hard_requirement: bool


@dataclass(slots=True)
class InitReport:
    """Structured diagnostics emitted during story graph initialization.

    Tracks materialized entity counts, dependency prelink results, and any hard
    or soft unresolved requirements discovered during initialization.
    """

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
    """Raised when eager initialization cannot satisfy hard requirements."""

    def __init__(self, report: InitReport):
        self.report = report
        super().__init__(
            "EAGER initialization failed: "
            f"{len(report.unresolved_hard)} unresolved hard dependencies"
        )


class ResolutionFailureReason(str, Enum):
    """Typed failure reasons for lazy destination wiring checks."""

    NO_TEMPLATE = "no_template"
    AMBIGUOUS_TEMPLATE = "ambiguous_template"


class ResolutionError(RuntimeError):
    """Raised when lazy destination wiring cannot resolve canonical targets."""

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
    """Final result of materializing a runtime story graph.

    Packages the graph, initialization report, resolved entry ids, and optional
    source/codec metadata carried forward from compilation.
    """

    graph: Any
    report: InitReport
    entry_ids: list[UUID]
    source_map: dict[str, Any] = field(default_factory=dict)
    codec_state: dict[str, Any] = field(default_factory=dict)
    codec_id: str | None = None
