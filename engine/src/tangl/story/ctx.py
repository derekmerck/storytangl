"""Story runtime context protocol contracts."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from tangl.core import TemplateRegistry
from tangl.vm.ctx import VmResolverCtx


@runtime_checkable
class StoryRuntimeCtx(VmResolverCtx, Protocol):
    """StoryRuntimeCtx()

    Structural protocol for story runtime helpers and handlers.

    Why
    ----
    Story-layer rendering and provisioning helpers need only a focused slice of
    the full vm context surface. This protocol documents that required accessor
    contract without coupling helpers to one concrete context implementation.
    """

    graph: Any

    @property
    def cursor(self) -> Any: ...

    def get_story_locals(self) -> Mapping[str, Any]: ...
    def get_location_entity_groups(self) -> Iterable[Iterable[Any]]: ...
    def get_template_scope_groups(self) -> Iterable[TemplateRegistry]: ...


__all__ = ["StoryRuntimeCtx"]
