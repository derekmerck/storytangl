"""VM handlers for sandbox dynamic choice projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from tangl.core import Selector, Token
from tangl.core.behavior import Priority
from tangl.core.runtime_op import Effect, Predicate
from tangl.journal.fragments import ContentFragment
from tangl.story import Action
from tangl.story.concepts.asset import AssetTransactionManager, HasAssets
from tangl.vm import ResolutionPhase, TraversableNode, VmPhaseCtx, on_provision, on_update
from tangl.vm.dispatch import on_compose_journal, on_gather_ns

from .location import (
    SandboxExit,
    SandboxLocation,
    SandboxLockable,
    normalize_sandbox_direction,
)
from .schedule import ScheduledEvent, ScheduledPresence
from .scope import SandboxScope
from .time import advance_world_turn, current_world_time
from .visibility import SandboxProjectionState, SandboxVisibilityRule


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


def _asset_key(asset: Token) -> str:
    return asset.get_label() or asset.token_from


def _asset_name(asset: Token) -> str:
    value = getattr(asset, "name", None)
    if isinstance(value, str) and value:
        return value
    return _asset_key(asset).replace("_", " ")


def _asset_portable(asset: Token) -> bool:
    return bool(getattr(asset, "portable", True))


def _asset_read_text(asset: Token) -> str | None:
    value = getattr(asset, "read_text", None)
    if isinstance(value, str) and value:
        return value
    if bool(getattr(asset, "readable", False)):
        describe = getattr(asset, "describe", None)
        if callable(describe):
            return str(describe())
    return None


def _asset_lit(asset: Token) -> bool:
    return bool(getattr(asset, "lit", False))


def _asset_is_light_source(asset: Token) -> bool:
    return bool(getattr(asset, "light_source", False))


def _asset_turn_on_text(asset: Token) -> str:
    value = getattr(asset, "turn_on_text", None)
    if isinstance(value, str) and value:
        return value
    return f"Your {_asset_name(asset)} is now on."


def _asset_turn_off_text(asset: Token) -> str:
    value = getattr(asset, "turn_off_text", None)
    if isinstance(value, str) and value:
        return value
    return f"Your {_asset_name(asset)} is now off."


def _clear_dynamic_sandbox_actions(
    location: SandboxLocation,
    *,
    action_kind: str,
    ctx: VmPhaseCtx,
) -> None:
    graph = location.graph
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
    return sorted(
        candidates,
        key=lambda item: (
            distance
            if (distance := graph.path_dist(location, item)) is not None
            else float("inf")
        ),
    )[0]


def _resolve_location_ref(location: SandboxLocation, target_ref: str) -> SandboxLocation | None:
    target = _resolve_ref(location, target_ref, kind=SandboxLocation)
    return target if isinstance(target, SandboxLocation) else None


def _resolve_traversable_ref(location: SandboxLocation, target_ref: str) -> TraversableNode | None:
    return _resolve_ref(location, target_ref, kind=TraversableNode)


def _exit_spec(value: str | SandboxExit | Mapping[str, Any]) -> SandboxExit:
    if isinstance(value, SandboxExit):
        return value
    if isinstance(value, Mapping):
        payload = dict(value)
        if "journal" in payload and "journal_text" not in payload:
            payload["journal_text"] = payload.pop("journal")
        return SandboxExit.model_validate(payload)
    return SandboxExit(target=value)


def _movement_text(
    direction: str,
    target: SandboxLocation,
    exit_spec: SandboxExit | None = None,
) -> str:
    if exit_spec is not None and exit_spec.text:
        return exit_spec.text
    canonical = normalize_sandbox_direction(direction)
    target_name = target.location_name or target.get_label()
    if canonical == "in":
        return f"Enter {target_name}"
    if canonical == "out":
        return f"Exit to {target_name}"
    return f"Go {canonical} to {target_name}"


def _message_exit_text(direction: str, exit_spec: SandboxExit) -> str:
    if exit_spec.text:
        return exit_spec.text
    canonical = normalize_sandbox_direction(direction)
    return f"Go {canonical}"


def _has_manual_link_action(
    location: SandboxLocation,
    *,
    target: SandboxLocation,
) -> bool:
    for edge in location.edges_out(Selector(has_kind=Action)):
        if _has_tags(edge, "dynamic", "sandbox", "movement"):
            continue
        if edge.successor is target:
            return True
    return False


def _sandbox_scopes(location: SandboxLocation) -> list[SandboxScope]:
    ancestors = getattr(location, "ancestors", [location])
    return [scope for scope in ancestors if isinstance(scope, SandboxScope)]


def _sandbox_scope_label(location: SandboxLocation) -> str:
    for scope in _sandbox_scopes(location):
        return scope.get_label()
    return location.sandbox_scope or location.get_label()


def _sandbox_contribution_hints(
    location: SandboxLocation,
    *,
    source: str,
    contribution: str,
    source_label: str | None = None,
    source_kind: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    hints: dict[str, Any] = {
        "source": source,
        "contribution": contribution,
        "scope": _sandbox_scope_label(location),
    }
    if source_label is not None:
        hints["source_label"] = source_label
    if source_kind is not None:
        hints["source_kind"] = source_kind
    hints.update(extra)
    return hints


def _nearest_scope_value(location: SandboxLocation, field_name: str, default: Any) -> Any:
    local_value = getattr(location, field_name, None)
    if local_value is not None:
        return local_value
    for scope in _sandbox_scopes(location):
        scope_value = getattr(scope, field_name, None)
        if scope_value is not None:
            return scope_value
    return default


def _scheduled_events(location: SandboxLocation, ctx: VmPhaseCtx) -> list[ScheduledEvent]:
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


def _visibility_rules(location: SandboxLocation) -> list[SandboxVisibilityRule]:
    rules: list[SandboxVisibilityRule] = []
    for scope in reversed(_sandbox_scopes(location)):
        rules.extend(scope.visibility_rules)
    rules.extend(location.visibility_rules)
    return rules


def _lockable_by_label(location: SandboxLocation, label: str) -> SandboxLockable | None:
    for lockable in location.lockables:
        if lockable.label == label:
            return lockable
    return None


def _lockable_locked(location: SandboxLocation, label: str) -> bool:
    lockable = _lockable_by_label(location, label)
    return bool(lockable and lockable.locked)


def _lockable_open(location: SandboxLocation, label: str) -> bool:
    lockable = _lockable_by_label(location, label)
    return bool(lockable and lockable.open)


def _player_asset_holder(location: SandboxLocation) -> HasAssets | None:
    for candidate in getattr(location, "ancestors", [location]):
        player_assets = getattr(candidate, "player_assets", None)
        if isinstance(player_assets, HasAssets):
            return player_assets
        locals_ = getattr(candidate, "locals", {})
        if isinstance(locals_, Mapping):
            for key in ("player_assets", "player", "player_inv_holder"):
                value = locals_.get(key)
                if isinstance(value, HasAssets):
                    return value
    return None


def _asset_inventory(holder: HasAssets | None) -> set[str]:
    if holder is None:
        return set()
    labels: set[str] = set()
    for key, asset in holder.assets.items():
        labels.add(str(key))
        labels.add(str(asset.token_from))
        label = asset.get_label()
        if label:
            labels.add(str(label))
    return labels


def _holder_has_lit_light_source(holder: HasAssets | None) -> bool:
    if holder is None:
        return False
    return any(
        _asset_is_light_source(asset) and _asset_lit(asset)
        for asset in holder.assets.values()
    )


def _location_lit(location: SandboxLocation) -> bool:
    if location.light:
        return True
    traits = getattr(location, "traits", set()) or set()
    if "light" in traits or "lit" in traits:
        return True
    return bool(location.locals.get("light", False))


def _visibility_ns(location: SandboxLocation, ctx: VmPhaseCtx) -> dict[str, Any]:
    player_assets = _player_asset_holder(location)
    ns = dict(ctx.get_ns(location))
    ns.update(
        {
            "location": location,
            "player_assets": player_assets,
            "sandbox_location_lit": _location_lit(location),
            "sandbox_has_lit_light_source": lambda: _holder_has_lit_light_source(
                player_assets
            ),
        }
    )
    return ns


def _projection_state(location: SandboxLocation, ctx: VmPhaseCtx) -> SandboxProjectionState:
    state = SandboxProjectionState()
    ns = _visibility_ns(location, ctx)
    for rule in _visibility_rules(location):
        if rule.active_in(ns):
            state = rule.apply_to(state)
    if state.journal_text is None and state.suppress_location_description:
        state.journal_text = location.dark_text
    return state


def _target_visited(target: TraversableNode) -> bool:
    return bool(target.locals.get("_visited", False))


def _concept_providers(location: SandboxLocation, ctx: VmPhaseCtx) -> list[Any]:
    ns = ctx.get_ns(location)
    providers = list(ns.values())
    for key in ("roles", "settings"):
        value = ns.get(key)
        if isinstance(value, dict):
            providers.extend(value.values())
    return providers


def _provider_scheduled_events(
    location: SandboxLocation,
    *,
    ctx: VmPhaseCtx,
) -> list[ScheduledEvent]:
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


def _selected_payload(ctx: VmPhaseCtx) -> Any:
    return ctx.selected_payload


def _sandbox_inventory(location: SandboxLocation) -> set[str]:
    inventory: set[str] = _asset_inventory(_player_asset_holder(location))
    for scope in reversed(getattr(location, "ancestors", [location])):
        locals_ = getattr(scope, "locals", {})
        if not isinstance(locals_, Mapping):
            continue
        for key in ("player_inv", "inventory", "inv"):
            value = locals_.get(key)
            if isinstance(value, str):
                inventory.add(value)
                continue
            try:
                inventory.update(str(item) for item in value or ())
            except TypeError:
                continue
    return inventory


def _take_asset(location: SandboxLocation, asset_label: str) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    return AssetTransactionManager().give_asset(location, player_assets, asset_label)


def _drop_asset(location: SandboxLocation, asset_label: str) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    return AssetTransactionManager().give_asset(player_assets, location, asset_label)


def _set_asset_lit(location: SandboxLocation, asset_label: str, lit: bool) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    asset = player_assets.get_asset(asset_label)
    if asset is None:
        raise KeyError(asset_label)
    setattr(asset, "lit", lit)
    return asset


@on_gather_ns(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def contribute_sandbox_inventory_helpers(*, caller, ctx, **_kw):
    """Publish simple sandbox inventory helpers for generated action predicates."""
    if not isinstance(caller, SandboxLocation):
        return None
    inventory = frozenset(_sandbox_inventory(caller))
    return {
        "sandbox_inventory": inventory,
        "sandbox_has_key": lambda key: str(key) in inventory,
        "sandbox_fixture_locked": lambda label: _lockable_locked(caller, str(label)),
        "sandbox_fixture_open": lambda label: _lockable_open(caller, str(label)),
        "sandbox_take_asset": lambda asset_label: _take_asset(caller, str(asset_label)),
        "sandbox_drop_asset": lambda asset_label: _drop_asset(caller, str(asset_label)),
        "sandbox_turn_on_asset": lambda asset_label: _set_asset_lit(
            caller,
            str(asset_label),
            True,
        ),
        "sandbox_turn_off_asset": lambda asset_label: _set_asset_lit(
            caller,
            str(asset_label),
            False,
        ),
    }


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

    for raw_direction, link in sorted(caller.links.items()):
        exit_spec = _exit_spec(link)
        direction = normalize_sandbox_direction(raw_direction)
        if exit_spec.kind == "message":
            Action(
                registry=graph,
                label=f"sandbox_move_{caller.get_label()}_{raw_direction}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=_message_exit_text(raw_direction, exit_spec),
                journal_text=exit_spec.journal_text or "",
                tags={"dynamic", "sandbox", "movement"},
                ui_hints=_sandbox_contribution_hints(
                    caller,
                    source="sandbox_link",
                    contribution="movement",
                    source_label=caller.get_label(),
                    source_kind="location",
                    direction=direction,
                    raw_direction=raw_direction,
                    kind="message",
                ),
            )
            continue
        if exit_spec.target is None:
            continue
        target = _resolve_location_ref(caller, exit_spec.target)
        if target is None:
            continue
        if _has_manual_link_action(caller, target=target):
            continue
        availability = []
        if exit_spec.through:
            availability.append(
                Predicate(expr=f"sandbox_fixture_open({exit_spec.through!r})")
            )
        Action(
            registry=graph,
            label=f"sandbox_move_{caller.get_label()}_{raw_direction}",
            predecessor_id=caller.uid,
            successor_id=target.uid,
            text=_movement_text(raw_direction, target, exit_spec),
            availability=availability,
            tags={"dynamic", "sandbox", "movement"},
            ui_hints=_sandbox_contribution_hints(
                caller,
                source="sandbox_link",
                contribution="movement",
                source_label=caller.get_label(),
                source_kind="location",
                direction=direction,
                raw_direction=raw_direction,
                target=target.get_label(),
                through=exit_spec.through,
            ),
        )
    return None


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_asset_actions(*, caller, ctx, **_kw):
    """Project present and carried assets into ordinary sandbox actions."""
    if not isinstance(caller, SandboxLocation):
        return None
    if not caller.auto_provision:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="asset", ctx=ctx)
    projection_state = _projection_state(caller, ctx)

    if not projection_state.suppress_asset_affordances:
        for asset_label, asset in sorted(caller.assets.items()):
            asset_name = _asset_name(asset)
            if _asset_portable(asset):
                Action(
                    registry=graph,
                    label=f"sandbox_take_{caller.get_label()}_{asset_label}",
                    predecessor_id=caller.uid,
                    successor_id=caller.uid,
                    text=f"Take {asset_name}",
                    effects=[Effect(expr=f"sandbox_take_asset({asset_label!r})")],
                    journal_text="Taken.",
                    tags={"dynamic", "sandbox", "asset", "take"},
                    ui_hints=_sandbox_contribution_hints(
                        caller,
                        source="sandbox_asset",
                        contribution="take",
                        source_label=asset_label,
                        source_kind="asset",
                        verb="take",
                        asset=asset_label,
                    ),
                )
            read_text = _asset_read_text(asset)
            if read_text:
                Action(
                    registry=graph,
                    label=f"sandbox_read_{caller.get_label()}_{asset_label}",
                    predecessor_id=caller.uid,
                    successor_id=caller.uid,
                    text=f"Read {asset_name}",
                    journal_text=read_text,
                    tags={"dynamic", "sandbox", "asset", "read"},
                    ui_hints=_sandbox_contribution_hints(
                        caller,
                        source="sandbox_asset",
                        contribution="read",
                        source_label=asset_label,
                        source_kind="asset",
                        verb="read",
                        asset=asset_label,
                    ),
                )

    player_assets = _player_asset_holder(caller)
    if player_assets is None:
        return None
    for asset_label, asset in sorted(player_assets.assets.items()):
        asset_name = _asset_name(asset)
        if _asset_is_light_source(asset):
            lit = _asset_lit(asset)
            Action(
                registry=graph,
                label=f"sandbox_light_{caller.get_label()}_{asset_label}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=f"Turn {'off' if lit else 'on'} {asset_name}",
                effects=[
                    Effect(
                        expr=(
                            f"sandbox_turn_off_asset({asset_label!r})"
                            if lit
                            else f"sandbox_turn_on_asset({asset_label!r})"
                        )
                    )
                ],
                journal_text=_asset_turn_off_text(asset) if lit else _asset_turn_on_text(asset),
                tags={"dynamic", "sandbox", "asset", "light"},
                ui_hints=_sandbox_contribution_hints(
                    caller,
                    source="sandbox_asset",
                    contribution="light",
                    source_label=asset_label,
                    source_kind="asset",
                    verb="turn_off" if lit else "turn_on",
                    asset=asset_label,
                ),
            )
        if not projection_state.suppress_asset_affordances:
            Action(
                registry=graph,
                label=f"sandbox_drop_{caller.get_label()}_{asset_label}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=f"Drop {asset_name}",
                effects=[Effect(expr=f"sandbox_drop_asset({asset_label!r})")],
                journal_text="Dropped.",
                tags={"dynamic", "sandbox", "asset", "drop"},
                ui_hints=_sandbox_contribution_hints(
                    caller,
                    source="sandbox_asset",
                    contribution="drop",
                    source_label=asset_label,
                    source_kind="asset",
                    verb="drop",
                    asset=asset_label,
                ),
            )
    return None


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_unlocks(*, caller, ctx, **_kw):
    """Project locked local objects into ordinary unlock actions."""
    if not isinstance(caller, SandboxLocation):
        return None
    if not caller.auto_provision:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="unlock", ctx=ctx)
    if _projection_state(caller, ctx).suppress_fixture_affordances:
        return None

    for lockable in caller.lockables:
        if not lockable.locked:
            continue
        Action(
            registry=graph,
            label=f"sandbox_unlock_{caller.get_label()}_{lockable.label}",
            predecessor_id=caller.uid,
            successor_id=caller.uid,
            text=lockable.action_text(),
            availability=[Predicate(expr=f"sandbox_has_key({lockable.key!r})")],
            effects=[Effect(expr=f"_s.unlock_lockable({lockable.label!r})")],
            journal_text=lockable.unlock_text,
            tags={"dynamic", "sandbox", "unlock"},
            ui_hints=_sandbox_contribution_hints(
                caller,
                source="sandbox_lockable",
                contribution="unlock",
                source_label=lockable.label,
                source_kind="fixture",
                target=lockable.label,
                key=lockable.key,
            ),
        )
    return None


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_fixture_actions(*, caller, ctx, **_kw):
    """Project openable local fixtures into ordinary sandbox actions."""
    if not isinstance(caller, SandboxLocation):
        return None
    if not caller.auto_provision:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="fixture", ctx=ctx)
    if _projection_state(caller, ctx).suppress_fixture_affordances:
        return None

    for lockable in caller.lockables:
        if not lockable.openable:
            continue
        if lockable.open:
            Action(
                registry=graph,
                label=f"sandbox_close_{caller.get_label()}_{lockable.label}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=lockable.close_text_label(),
                effects=[Effect(expr=f"_s.close_lockable({lockable.label!r})")],
                journal_text=lockable.close_text,
                tags={"dynamic", "sandbox", "fixture", "close"},
                ui_hints=_sandbox_contribution_hints(
                    caller,
                    source="sandbox_lockable",
                    contribution="close",
                    source_label=lockable.label,
                    source_kind="fixture",
                    target=lockable.label,
                ),
            )
            continue
        Action(
            registry=graph,
            label=f"sandbox_open_{caller.get_label()}_{lockable.label}",
            predecessor_id=caller.uid,
            successor_id=caller.uid,
            text=lockable.open_text_label(),
            availability=[Predicate(expr=f"not sandbox_fixture_locked({lockable.label!r})")],
            effects=[Effect(expr=f"_s.open_lockable({lockable.label!r})")],
            journal_text=lockable.open_text,
            tags={"dynamic", "sandbox", "fixture", "open"},
            ui_hints=_sandbox_contribution_hints(
                caller,
                source="sandbox_lockable",
                contribution="open",
                source_label=lockable.label,
                source_kind="fixture",
                target=lockable.label,
            ),
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
        ui_hints=_sandbox_contribution_hints(
            caller,
            source="sandbox_wait",
            contribution="wait",
            source_label=_sandbox_scope_label(caller),
            source_kind="scope",
        ),
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
            return_phase=ResolutionPhase.PLANNING if event.return_to_location else None,
            text=event.action_text(),
            tags={"dynamic", "sandbox", "event"},
            ui_hints=_sandbox_contribution_hints(
                caller,
                source="sandbox_schedule",
                contribution="event",
                source_label=event.label or event.target,
                source_kind="schedule",
                event=event.label,
                target=target.get_label(),
            ),
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

    try:
        turn_delta = int(payload.get("turn_delta", 1))
    except (TypeError, ValueError):
        turn_delta = 1
    if turn_delta < 0:
        return None
    advance_world_turn(_time_owner(caller), turn_delta)
    return None


@on_compose_journal(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
    priority=Priority.LATE,
)
def compose_sandbox_visibility_journal(*, caller, ctx, fragments, **_kw):
    """Substitute sandbox journal text when visibility rules suppress detail."""
    if not isinstance(caller, SandboxLocation):
        return None
    projection_state = _projection_state(caller, ctx)
    if not projection_state.suppress_location_description:
        return None
    if not projection_state.journal_text:
        return None

    composed: list[Any] = []
    replaced = False
    for fragment in fragments:
        if (
            isinstance(fragment, ContentFragment)
            and getattr(fragment, "source_id", None) == caller.uid
            and not replaced
        ):
            composed.append(
                ContentFragment(content=projection_state.journal_text, source_id=caller.uid)
            )
            replaced = True
            continue
        composed.append(fragment)
    if not replaced:
        composed.insert(
            0,
            ContentFragment(content=projection_state.journal_text, source_id=caller.uid),
        )
    return composed
