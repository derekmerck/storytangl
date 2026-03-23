from __future__ import annotations

from enum import StrEnum
from typing import Any, Callable

from tangl.core import Entity, EntityTemplate

from ..ctx import VmPhaseCtx
from .provisioner import _next_provision_uid, _template_hash_value


class MaterializeRole(StrEnum):
    """Canonical roles for shared template materialization flows."""

    INIT = "init"
    PROVISION_INTERMEDIATE = "provision_intermediate"
    PROVISION_LEAF = "provision_leaf"


def resolve_story_materialize_hook(
    _ctx: VmPhaseCtx | None,
) -> Callable[[EntityTemplate, Any], Entity] | None:
    """Return an optional story-specific materializer hook from ``_ctx``."""
    if _ctx is None:
        return None
    graph = _ctx.graph
    factory = getattr(graph, "factory", None)
    factory_hook = getattr(factory, "story_materialize_template", None)
    if callable(factory_hook):
        return factory_hook
    graph_hook = getattr(graph, "story_materialize", None)
    if callable(graph_hook):
        return graph_hook
    return None


def resolve_story_post_materialize_hook(
    _ctx: VmPhaseCtx | None,
) -> Callable[..., Any] | None:
    """Return an optional story post-materialization hook from ``_ctx``."""
    if _ctx is None:
        return None
    graph = _ctx.graph
    factory = getattr(graph, "factory", None)
    factory_hook = getattr(factory, "story_post_materialize", None)
    if callable(factory_hook):
        return factory_hook
    graph_hook = getattr(graph, "story_post_materialize", None)
    if callable(graph_hook):
        return graph_hook
    return None


def resolve_story_preview_requirement_hook(
    _ctx: VmPhaseCtx | None,
) -> Callable[..., Any] | None:
    """Return an optional story preview hook from ``_ctx``."""
    if _ctx is None:
        return None
    graph = _ctx.graph
    factory = getattr(graph, "factory", None)
    factory_hook = getattr(factory, "preview_requirement_contract", None)
    if callable(factory_hook):
        return factory_hook
    graph_hook = getattr(graph, "story_preview_requirement", None)
    if callable(graph_hook):
        return graph_hook
    return None


def materialize_template_entity(
    template: EntityTemplate,
    *,
    _ctx: Any = None,
    role: MaterializeRole | str = MaterializeRole.PROVISION_LEAF,
    story_materialize: Callable[[EntityTemplate, Any], Entity] | None = None,
) -> Entity:
    """Materialize one template using the shared VM provisioning contract."""
    if isinstance(role, str):
        role = MaterializeRole(role)

    if role in (MaterializeRole.INIT, MaterializeRole.PROVISION_INTERMEDIATE):
        provider = template.materialize(uid=_next_provision_uid(_ctx=_ctx))
    elif role is MaterializeRole.PROVISION_LEAF:
        if callable(story_materialize):
            provider = story_materialize(template, _ctx)
        else:
            provider = template.materialize(uid=_next_provision_uid(_ctx=_ctx))
    else:
        raise ValueError(f"Unsupported materialization role: {role!r}")

    if not isinstance(provider, Entity):
        raise TypeError("Template materialization must yield Entity-compatible providers")
    provider.templ_hash = _template_hash_value(template)
    return provider


def attach_child(parent: Any, child: Any) -> None:
    """Attach ``child`` to ``parent`` and finalize container contracts when present."""
    if parent is None or not hasattr(parent, "add_child"):
        return
    parent.add_child(child)
    finalize = getattr(parent, "finalize_container_contract", None)
    if callable(finalize):
        finalize()
