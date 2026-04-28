"""VM runtime context protocol."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Protocol, runtime_checkable
from uuid import UUID

from tangl.core import TemplateRegistry
from tangl.core.ctx import DispatchCtx

if TYPE_CHECKING:
    from .runtime.frame import PhaseCtx


@runtime_checkable
class VmPhaseCtx(DispatchCtx, Protocol):
    """Canonical runtime context implemented by :class:`PhaseCtx`."""

    graph: Any
    cursor_id: UUID | None
    step: int | None
    current_phase: Any
    correlation_id: UUID | str | None
    logger: Any | None
    meta: Mapping[str, Any] | None
    incoming_edge: Any | None
    selected_edge: Any | None
    selected_payload: Any

    @property
    def cursor(self) -> Any | None: ...

    def get_meta(self) -> Mapping[str, Any]: ...

    def get_ns(self, node: Any = None) -> Mapping[str, Any]:
        """Return the assembled scoped namespace for a node."""
        ...

    def get_random(self) -> Random: ...
    def get_location_entity_groups(self) -> Iterable[Iterable[Any]]: ...
    def get_template_scope_groups(self) -> Iterable[TemplateRegistry]: ...
    def get_token_catalogs(self, *, requirement: Any = None) -> Iterable[Any]: ...
    def get_media_inventories(self, *, requirement: Any = None) -> Iterable[Any]: ...

    def derive(
        self,
        *,
        cursor_id: UUID | None = None,
        graph: Any | None = None,
        meta_overrides: Mapping[str, Any] | None = None,
        **field_overrides: Any,
    ) -> "PhaseCtx": ...


__all__ = ["VmPhaseCtx"]
