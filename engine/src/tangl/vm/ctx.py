"""VM context protocol contracts."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Protocol, runtime_checkable
from uuid import UUID

from tangl.core.ctx import CoreCtx, DispatchCtx
from tangl.core import TemplateRegistry

if TYPE_CHECKING:
    from .runtime.frame import PhaseCtx


@runtime_checkable
class VmDispatchCtx(DispatchCtx, Protocol):
    """Minimal context contract required by vm phase dispatch hooks."""


@runtime_checkable
class VmResolverCtx(VmDispatchCtx, CoreCtx, Protocol):
    """Context contract required by vm provision resolver."""

    def get_location_entity_groups(self) -> Iterable[Iterable[Any]]: ...
    def get_template_scope_groups(self) -> Iterable[TemplateRegistry]: ...


@runtime_checkable
class VmPhaseCtx(VmResolverCtx, Protocol):
    """Context contract used by phase handlers during one follow-edge pass."""

    graph: Any
    cursor_id: UUID
    step: int
    current_phase: Any
    selected_edge: Any | None
    selected_payload: Any

    @property
    def cursor(self) -> Any: ...

    def get_ns(self, node: Any = None) -> Mapping[str, Any]:
        """Return the assembled scoped namespace for a node."""
        ...

    def get_random(self) -> Random: ...


@runtime_checkable
class VmRequirementStampCtx(Protocol):
    """Minimal context contract for requirement resolution metadata stamping."""

    step: int | None
    cursor_id: UUID | None


@runtime_checkable
class VmDerivedPhaseCtx(VmResolverCtx, VmRequirementStampCtx, Protocol):
    """Context that can derive a child :class:`PhaseCtx` for nested validation."""

    graph: Any
    correlation_id: UUID | str | None
    logger: Any | None
    meta: Mapping[str, Any] | None

    def derive(
        self,
        *,
        cursor_id: UUID | None = None,
        graph: Any | None = None,
        meta_overrides: Mapping[str, Any] | None = None,
        **field_overrides: Any,
    ) -> "PhaseCtx": ...


__all__ = [
    "VmDerivedPhaseCtx",
    "VmDispatchCtx",
    "VmPhaseCtx",
    "VmRequirementStampCtx",
    "VmResolverCtx",
]
