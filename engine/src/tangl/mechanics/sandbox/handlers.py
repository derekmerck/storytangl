"""VM handlers for sandbox dynamic choice projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from tangl.core import Selector
from tangl.story import Action
from tangl.vm import ResolutionPhase, TraversableNode, VmPhaseCtx, on_provision, on_update

from .location import SandboxLocation
from .schedule import ScheduledEvent, ScheduledPresence
from .scope import SandboxScope
from .time import advance_world_turn, current_world_time


@runtime_checkable
class SandboxEventProvider(Protocol):
    """Concept provider that can donate sandbox events."""

    def get_sandbox_events(
        self,
        *,
        caller: SandboxLocation,
        ctx: VmPhaseCtx,
        ns: Mapping[str, Any],
    ) -> list[ScheduledEvent] | None:
        """Return sandbox events available from this provider."""
        ...


def _has_tags(value: Any, *tags: str) -> bool:
    actual = getattr(value, "tags", set()) or set()
    return set(tags).issubset(actual)


def _clear_dynamic_sandbox_actions(
    location: SandboxLocation,
    *,
    action_kind: str,
    ctx: Any,
) -> None:
    graph = getattr(location, "graph", None)
    if graph is None:
        return

    for edge in list(location.edges_out(Selector(has_kind=Action))):
        if _has_tags(edge, "dynamic", "sandbox", action_kind):
            graph.remove(edge.uid, _ctx=ctx)


def _resolve_ref(
    location: SandboxLocation,
    target_ref: str,
    *,
    kind: type[TraversableNode],
) -> TraversableNode | None:
    graph = getattr(location, "graph", None)
    if graph is None:
        return None

    candidates = [
        candidate
        for candidate in graph.find_all(Selector.from_identifier(target_ref))
        if isinstance(candidate, kind)
    ]
    if not candidates and "." not in target_ref:
        scoped_ref = f"{location.sandbox_scope}.{target_ref}" if location.sandbox_scope else None
        if scoped_ref:
            candidates = [
                candidate
                for candidate in graph.find_all(Selector.from_identifier(scoped_ref))
                if isinstance(candidate, kind)
            ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: graph.path_dist(location, item))[0]


def _resolve_location_ref(location: SandboxLocation, target_ref: str) -> SandboxLocation | None:
    target = _resolve_ref(location, target_ref, kind=SandboxLocation)
    return target if isinstance(target, SandboxLocation) else None


def _resolve_traversable_ref(location: SandboxLocation, target_ref: str) -> TraversableNode | None:
    return _resolve_ref(location, target_ref, kind=TraversableNode)


def _movement_text(direction: str, target: SandboxLocation) -> str:
    target_name = target.location_name or target.get_label()
    return f"Go {direction} to {target_name}"


def _sandbox_scopes(location: SandboxLocation) -> list[SandboxScope]:
    ancestors = getattr(location, "ancestors", [location])
    return [scope for scope in ancestors if isinstance(scope, SandboxScope)]


def _nearest_scope_value(location: SandboxLocation, field_name: str, default: Any) -> Any:
    local_value = getattr(location, field_name, None)
    if local_value is not None:
        return local_value
    for scope in _sandbox_scopes(location):
        scope_value = getattr(scope, field_name, None)
        if scope_value is not None:
            return scope_value
    return default


def _scheduled_events(location: SandboxLocation, ctx: Any) -> list[ScheduledEvent]:
    events: list[ScheduledEvent] = []
    for scope in reversed(_sandbox_scopes(location)):
        events.extend(scope.scheduled_events)
    events.extend(location.scheduled_events)
    events.extend(_provider_scheduled_events(location, ctx=ctx))
    return events


def _scheduled_presence(location: SandboxLocation) -> list[ScheduledPresence]:
    presence: list[ScheduledPresence] = []
    for scope in reversed(_sandbox_scopes(location)):
        presence.extend(scope.scheduled_presence)
    return presence


def _actors_present(location: SandboxLocation) -> list[str]:
    world_time = current_world_time(location)
    location_label = location.get_label()
    actors: list[str] = []
    for entry in _scheduled_presence(location):
        if entry.matches(world_time, location=location_label):
            actors.append(entry.actor)
    return actors


def _time_owner(location: SandboxLocation) -> Any:
    for candidate in getattr(location, "ancestors", [location]):
        if isinstance(candidate, SandboxScope):
            return candidate
    return location


def _target_visited(target: TraversableNode) -> bool:
    return bool(target.locals.get("_visited", False))


def _concept_providers(location: SandboxLocation, ctx: Any) -> list[Any]:
    ns = ctx.get_ns(location)
    providers = list(ns.values())
    for key in ("roles", "settings"):
        value = ns.get(key)
        if isinstance(value, dict):
            providers.extend(value.values())
    return providers


def _provider_scheduled_events(location: SandboxLocation, *, ctx: Any) -> list[ScheduledEvent]:
    events: list[ScheduledEvent] = []
    seen_provider_ids: set[int] = set()
    ns = ctx.get_ns(location)
    for provider in _concept_providers(location, ctx):
        provider_id = id(provider)
        if provider_id in seen_provider_ids:
            continue
        seen_provider_ids.add(provider_id)

        if not isinstance(provider, SandboxEventProvider):
            continue

        provided = provider.get_sandbox_events(caller=location, ctx=ctx, ns=ns)
        if provided is None:
            continue
        for event in provided:
            if not isinstance(event, ScheduledEvent):
                raise TypeError("get_sandbox_events must yield ScheduledEvent instances")
            events.append(event)
    return events


def _selected_payload(ctx: Any) -> Any:
    payload = getattr(ctx, "selected_payload", None)
    if payload is not None:
        return payload

    selected_edge = getattr(ctx, "selected_edge", None)
    if selected_edge is not None:
        return getattr(selected_edge, "payload", None)

    incoming_edge = getattr(ctx, "incoming_edge", None)
    if incoming_edge is not None:
        return getattr(incoming_edge, "payload", None)

    return None


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

    _clear_dynamic_sandbox_actions(caller, action_kind="movement", ctx=ctx)

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


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_wait(*, caller, ctx, **_kw):
    """Project a normal self-loop wait action for sandbox locations."""
    if not isinstance(caller, SandboxLocation):
        return None
    wait_enabled = bool(_nearest_scope_value(caller, "wait_enabled", True))
    if not caller.auto_provision or not wait_enabled:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="wait", ctx=ctx)

    wait_text = str(_nearest_scope_value(caller, "wait_text", "Wait"))
    turn_delta = int(_nearest_scope_value(caller, "wait_turn_delta", 1))
    Action(
        registry=graph,
        label=f"sandbox_wait_{caller.get_label()}",
        predecessor_id=caller.uid,
        successor_id=caller.uid,
        text=wait_text,
        payload={
            "sandbox_action": "wait",
            "turn_delta": turn_delta,
        },
        tags={"dynamic", "sandbox", "wait"},
        ui_hints={"source": "sandbox_wait"},
    )
    return None


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_scheduled_events(*, caller, ctx, **_kw):
    """Project matching scheduled events into normal dynamic actions."""
    if not isinstance(caller, SandboxLocation):
        return None
    if not caller.auto_provision:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="event", ctx=ctx)

    world_time = current_world_time(caller)
    location_label = caller.get_label()
    actors_present = _actors_present(caller)
    for index, event in enumerate(_scheduled_events(caller, ctx)):
        if not event.matches(
            world_time,
            location=location_label,
            actors_present=actors_present,
        ):
            continue
        target = _resolve_traversable_ref(caller, event.target)
        if target is None:
            continue
        if event.once and _target_visited(target):
            continue
        Action(
            registry=graph,
            label=f"sandbox_event_{caller.get_label()}_{index}",
            predecessor_id=caller.uid,
            successor_id=target.uid,
            trigger_phase=Action.trigger_phase_from_activation(event.activation),
            return_phase=ResolutionPhase.UPDATE if event.return_to_location else None,
            text=event.action_text(),
            tags={"dynamic", "sandbox", "event"},
            ui_hints={
                "source": "sandbox_schedule",
                "event": event.label,
                "target": target.get_label(),
            },
        )
    return None


@on_update(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def advance_sandbox_time_on_wait(*, caller, ctx, **_kw):
    """Advance sandbox world time when the selected action is wait."""
    if not isinstance(caller, SandboxLocation):
        return None

    payload = _selected_payload(ctx)
    if not isinstance(payload, dict):
        return None
    if payload.get("sandbox_action") != "wait":
        return None

    advance_world_turn(_time_owner(caller), int(payload.get("turn_delta", 1)))
    return None
