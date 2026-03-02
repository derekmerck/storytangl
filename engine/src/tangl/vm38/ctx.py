"""VM context protocol contracts."""

from __future__ import annotations

from random import Random
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable
from uuid import UUID

from tangl.core38.ctx import CoreCtx, DispatchCtx
from tangl.core38 import TemplateRegistry


@runtime_checkable
class VmDispatchCtx(DispatchCtx, Protocol):
    """Minimal context contract required by vm38 dispatch hooks."""


@runtime_checkable
class VmResolverCtx(VmDispatchCtx, CoreCtx, Protocol):
    """Context contract required by vm38 provision resolver."""

    def get_location_entity_groups(self) -> Iterable[Iterable[Any]]: ...
    def get_template_scope_groups(self) -> Iterable[TemplateRegistry]: ...
    # Legacy aliases retained as compatibility bridges.
    def get_entity_groups(self) -> Iterable[Iterable[Any]]: ...
    def get_template_groups(self) -> Iterable[TemplateRegistry]: ...


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

    def get_ns(self, node: Any = None) -> Mapping[str, Any]: ...
    def get_random(self) -> Random: ...


__all__ = [
    "VmDispatchCtx",
    "VmPhaseCtx",
    "VmResolverCtx",
]
