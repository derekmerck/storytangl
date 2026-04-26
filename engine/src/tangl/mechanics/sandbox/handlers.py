"""VM handlers for sandbox dynamic choice projection."""

from __future__ import annotations

from typing import Any

from tangl.core import Selector
from tangl.story import Action
from tangl.vm import on_provision

from .location import SandboxLocation


def _has_tags(value: Any, *tags: str) -> bool:
    actual = getattr(value, "tags", set()) or set()
    return set(tags).issubset(actual)


def _clear_dynamic_sandbox_actions(location: SandboxLocation, *, ctx: Any) -> None:
    graph = getattr(location, "graph", None)
    if graph is None:
        return

    for edge in list(location.edges_out(Selector(has_kind=Action, trigger_phase=None))):
        if _has_tags(edge, "dynamic", "sandbox", "movement"):
            graph.remove(edge.uid, _ctx=ctx)


def _resolve_location_ref(location: SandboxLocation, target_ref: str) -> SandboxLocation | None:
    graph = getattr(location, "graph", None)
    if graph is None:
        return None

    candidates = list(graph.find_all(Selector.from_identifier(target_ref)))
    candidates = [candidate for candidate in candidates if isinstance(candidate, SandboxLocation)]
    if not candidates and "." not in target_ref:
        scoped_ref = f"{location.sandbox_scope}.{target_ref}" if location.sandbox_scope else None
        if scoped_ref:
            candidates = [
                candidate
                for candidate in graph.find_all(Selector.from_identifier(scoped_ref))
                if isinstance(candidate, SandboxLocation)
            ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: graph.path_dist(location, item))[0]


def _movement_text(direction: str, target: SandboxLocation) -> str:
    target_name = target.location_name or target.get_label()
    return f"Go {direction} to {target_name}"


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_location_links(*, caller, ctx, **_kw):
    """Project sandbox location links into ordinary dynamic movement actions."""
    if not isinstance(caller, SandboxLocation):
        return None
    if not caller.auto_provision:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, ctx=ctx)

    for direction, target_ref in sorted(caller.links.items()):
        target = _resolve_location_ref(caller, target_ref)
        if target is None:
            continue
        Action(
            registry=graph,
            label=f"sandbox_move_{caller.get_label()}_{direction}",
            predecessor_id=caller.uid,
            successor_id=target.uid,
            text=_movement_text(direction, target),
            tags={"dynamic", "sandbox", "movement"},
            ui_hints={
                "source": "sandbox_link",
                "direction": direction,
                "target": target.get_label(),
            },
        )
    return None
