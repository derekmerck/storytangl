"""VM handlers for sandbox dynamic choice projection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from tangl.core import Graph, Selector, Token
from tangl.core.behavior import Priority
from tangl.core.runtime_op import Effect, Predicate
from tangl.journal.fragments import ContentFragment
from tangl.story import Action
from tangl.story.concepts.asset import AssetTransactionManager, HasAssets
from tangl.vm import ResolutionPhase, TraversableNode, VmPhaseCtx, on_provision, on_update
from tangl.vm.dispatch import on_compose_journal, on_gather_ns

from .facets import ContainerFacet, LightSourceFacet, SwitchableFacet
from .location import (
    SandboxExit,
    SandboxFixture,
    SandboxLocation,
    normalize_sandbox_direction,
)
from .mob import SandboxMob
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


class TaggedEntity(Protocol):
    """Entity surface for tag-based dynamic sandbox cleanup."""

    tags: set[Any]


class SandboxAssetSurface(Protocol):
    """Token surface expected by sandbox asset affordance projection."""

    token_from: str
    name: str
    traits: set[str]
    portable: bool
    readable: bool
    read_text: str | None
    switchable: SwitchableFacet | None
    light_source: LightSourceFacet | None
    container: ContainerFacet | None
    lit: bool
    turn_on_text: str | None
    turn_off_text: str | None
    take_text: str | None
    drop_text: str | None

    def get_label(self) -> str | None:
        """Return the graph/token label."""
        ...


def _has_tags(value: TaggedEntity, *tags: str) -> bool:
    return set(tags).issubset(value.tags or set())


def _asset_key(asset: SandboxAssetSurface) -> str:
    return asset.get_label() or asset.token_from


def _asset_name(asset: SandboxAssetSurface) -> str:
    if asset.name:
        return asset.name
    return _asset_key(asset).replace("_", " ")


def _asset_portable(asset: SandboxAssetSurface) -> bool:
    return asset.portable


def _asset_read_text(asset: SandboxAssetSurface) -> str | None:
    return asset.read_text if asset.readable else None


def _asset_lit(asset: SandboxAssetSurface) -> bool:
    return asset.lit


def _asset_is_switchable(asset: SandboxAssetSurface) -> bool:
    return asset.switchable is not None


def _asset_is_container(asset: SandboxAssetSurface) -> bool:
    return asset.container is not None


def _asset_illuminates(asset: SandboxAssetSurface) -> bool:
    return bool(
        asset.light_source
        and asset.light_source.illuminates(
            is_on=asset.lit,
            switchable=asset.switchable,
        )
    )


def _asset_turn_on_text(asset: SandboxAssetSurface) -> str:
    if asset.turn_on_text:
        return asset.turn_on_text
    return f"Your {_asset_name(asset)} is now on."


def _asset_turn_off_text(asset: SandboxAssetSurface) -> str:
    if asset.turn_off_text:
        return asset.turn_off_text
    return f"Your {_asset_name(asset)} is now off."


def _asset_take_text(asset: SandboxAssetSurface) -> str:
    return asset.take_text or "Taken."


def _asset_drop_text(asset: SandboxAssetSurface) -> str:
    return asset.drop_text or "Dropped."


def _asset_container_open_text(asset: SandboxAssetSurface) -> str:
    container = asset.container
    if container and container.open_text:
        return container.open_text
    return "Opened."


def _asset_container_close_text(asset: SandboxAssetSurface) -> str:
    container = asset.container
    if container and container.close_text:
        return container.close_text
    return "Closed."


def _asset_container_action_text(asset: SandboxAssetSurface) -> str:
    container = asset.container
    asset_name = _asset_name(asset)
    if container and container.is_open:
        return container.close_action_text or f"Close {asset_name}"
    if container:
        return container.open_action_text or f"Open {asset_name}"
    return f"Open {asset_name}"


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
        if "to" in payload and "target" not in payload:
            payload["target"] = payload.pop("to")
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
        if _has_tags(edge, "dynamic"):
            continue
        if edge.successor is target:
            return True
    return False


def _sandbox_scopes(location: SandboxLocation) -> list[SandboxScope]:
    return [scope for scope in location.ancestors if isinstance(scope, SandboxScope)]


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


def _nearest_wait_enabled(location: SandboxLocation) -> bool:
    if location.wait_enabled is not None:
        return location.wait_enabled
    for scope in _sandbox_scopes(location):
        if scope.wait_enabled is not None:
            return scope.wait_enabled
    return True


def _nearest_wait_text(location: SandboxLocation) -> str:
    if location.wait_text is not None:
        return location.wait_text
    for scope in _sandbox_scopes(location):
        if scope.wait_text is not None:
            return scope.wait_text
    return "Wait"


def _nearest_wait_turn_delta(location: SandboxLocation) -> int:
    if location.wait_turn_delta is not None:
        return location.wait_turn_delta
    for scope in _sandbox_scopes(location):
        if scope.wait_turn_delta is not None:
            return scope.wait_turn_delta
    return 1


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


def _sandbox_mobs(location: SandboxLocation) -> list[SandboxMob]:
    mobs: list[SandboxMob] = []
    for scope in reversed(_sandbox_scopes(location)):
        mobs.extend(scope.mobs)
    return mobs


def _present_mobs(location: SandboxLocation) -> list[SandboxMob]:
    location_label = location.get_label()
    return [mob for mob in _sandbox_mobs(location) if mob.present_at(location_label)]


def _mob_by_label(location: SandboxLocation, label: str) -> SandboxMob | None:
    for mob in _sandbox_mobs(location):
        if mob.get_label() == label:
            return mob
    return None


def _mob_affordance_tag(label: str) -> str | None:
    normalized = label.strip().replace(" ", "_")
    if not normalized:
        return None
    return f"affordance:{normalized}"


def _time_owner(location: SandboxLocation) -> Any:
    for candidate in location.ancestors:
        if isinstance(candidate, SandboxScope):
            return candidate
    return location


def _visibility_rules(location: SandboxLocation) -> list[SandboxVisibilityRule]:
    rules: list[SandboxVisibilityRule] = []
    for scope in reversed(_sandbox_scopes(location)):
        rules.extend(scope.visibility_rules)
    rules.extend(location.visibility_rules)
    return rules


def _fixture_by_label(location: SandboxLocation, label: str) -> SandboxFixture | None:
    for fixture in location.fixtures:
        if fixture.label == label:
            return fixture
    return None


def _fixture_locked(location: SandboxLocation, label: str) -> bool:
    fixture = _fixture_by_label(location, label)
    return bool(fixture and fixture.locked)


def _fixture_open(location: SandboxLocation, label: str) -> bool:
    fixture = _fixture_by_label(location, label)
    return bool(fixture and fixture.open)


def _fixture_can_unlock(location: SandboxLocation, label: str) -> bool:
    fixture = _fixture_by_label(location, label)
    inventory = _sandbox_inventory(location)
    return bool(fixture and fixture.can_unlock(has_key=lambda key: key in inventory))


def _fixture_can_open(location: SandboxLocation, label: str) -> bool:
    fixture = _fixture_by_label(location, label)
    inventory = _sandbox_inventory(location)
    return bool(fixture and fixture.can_open(has_key=lambda key: key in inventory))


def _fixture_can_close(location: SandboxLocation, label: str) -> bool:
    fixture = _fixture_by_label(location, label)
    return bool(fixture and fixture.can_close())


def _fixture_can_receive_asset(
    location: SandboxLocation,
    fixture_label: str,
    asset_label: str,
) -> bool:
    fixture = _fixture_by_label(location, fixture_label)
    player_assets = _player_asset_holder(location)
    if fixture is None or player_assets is None:
        return False
    asset = player_assets.get_asset(asset_label)
    return bool(asset and fixture.can_receive_asset(asset, player_assets))


def _player_asset_holder(location: SandboxLocation) -> HasAssets | None:
    for candidate in location.ancestors:
        if isinstance(candidate, SandboxScope):
            return candidate.player_assets
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
    return any(_asset_illuminates(asset) for asset in holder.assets.values())


def _location_lit(location: SandboxLocation) -> bool:
    if location.light:
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
    return _asset_inventory(_player_asset_holder(location))


def _player_asset(location: SandboxLocation, asset_label: str) -> Token | None:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        return None
    return player_assets.get_asset(asset_label)


def _player_asset_container(
    location: SandboxLocation,
    container_label: str,
) -> ContainerFacet | None:
    asset = _player_asset(location, container_label)
    if asset is None:
        return None
    return asset.container


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


def _put_asset_in_fixture(
    location: SandboxLocation,
    fixture_label: str,
    asset_label: str,
) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    fixture = location.fixture_by_label(fixture_label)
    return AssetTransactionManager().give_asset(player_assets, fixture, asset_label)


def _take_asset_from_fixture(
    location: SandboxLocation,
    fixture_label: str,
    asset_label: str,
) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    fixture = location.fixture_by_label(fixture_label)
    return AssetTransactionManager().give_asset(fixture, player_assets, asset_label)


def _asset_container_can_receive(
    location: SandboxLocation,
    container_label: str,
    asset_label: str,
) -> bool:
    container = _player_asset_container(location, container_label)
    asset = _player_asset(location, asset_label)
    return bool(container and asset and container.can_receive_asset(asset))


def _put_asset_in_asset_container(
    location: SandboxLocation,
    container_label: str,
    asset_label: str,
) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    container = _player_asset_container(location, container_label)
    if container is None:
        raise ValueError(f"Asset {container_label!r} is not a container")
    return AssetTransactionManager().give_asset(player_assets, container, asset_label)


def _take_asset_from_asset_container(
    location: SandboxLocation,
    container_label: str,
    asset_label: str,
) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    container = _player_asset_container(location, container_label)
    if container is None:
        raise ValueError(f"Asset {container_label!r} is not a container")
    return AssetTransactionManager().give_asset(container, player_assets, asset_label)


def _set_asset_container_open(
    location: SandboxLocation,
    container_label: str,
    is_open: bool,
) -> Token:
    asset = _player_asset(location, container_label)
    if asset is None:
        raise KeyError(container_label)
    container = asset.container
    if container is None:
        raise ValueError(f"Asset {container_label!r} is not a container")
    if is_open:
        container.open()
    else:
        container.close()
    return asset


def _set_asset_lit(location: SandboxLocation, asset_label: str, lit: bool) -> Token:
    player_assets = _player_asset_holder(location)
    if player_assets is None:
        raise ValueError("sandbox location has no player asset holder")
    asset = player_assets.get_asset(asset_label)
    if asset is None:
        raise KeyError(asset_label)
    if asset.switchable is None:
        raise ValueError(f"Asset {asset_label!r} is not switchable")
    if lit:
        asset.switchable.switch_on(asset)
    else:
        asset.switchable.switch_off(asset)
    return asset


def _set_mob_state(
    location: SandboxLocation,
    mob_label: str,
    state_key: str,
    value: Any,
) -> Any:
    mob = _mob_by_label(location, mob_label)
    if mob is None:
        raise KeyError(mob_label)
    return mob.set_state_value(state_key, value)


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
        "sandbox_fixture_locked": lambda label: _fixture_locked(caller, str(label)),
        "sandbox_fixture_open": lambda label: _fixture_open(caller, str(label)),
        "sandbox_fixture_can_unlock": lambda label: _fixture_can_unlock(
            caller,
            str(label),
        ),
        "sandbox_fixture_can_open": lambda label: _fixture_can_open(
            caller,
            str(label),
        ),
        "sandbox_fixture_can_close": lambda label: _fixture_can_close(
            caller,
            str(label),
        ),
        "sandbox_fixture_can_receive_asset": (
            lambda fixture_label, asset_label: _fixture_can_receive_asset(
                caller,
                str(fixture_label),
                str(asset_label),
            )
        ),
        "sandbox_take_asset": lambda asset_label: _take_asset(caller, str(asset_label)),
        "sandbox_drop_asset": lambda asset_label: _drop_asset(caller, str(asset_label)),
        "sandbox_put_asset_in_fixture": (
            lambda fixture_label, asset_label: _put_asset_in_fixture(
                caller,
                str(fixture_label),
                str(asset_label),
            )
        ),
        "sandbox_take_asset_from_fixture": (
            lambda fixture_label, asset_label: _take_asset_from_fixture(
                caller,
                str(fixture_label),
                str(asset_label),
            )
        ),
        "sandbox_asset_container_can_receive": (
            lambda container_label, asset_label: _asset_container_can_receive(
                caller,
                str(container_label),
                str(asset_label),
            )
        ),
        "sandbox_put_asset_in_asset_container": (
            lambda container_label, asset_label: _put_asset_in_asset_container(
                caller,
                str(container_label),
                str(asset_label),
            )
        ),
        "sandbox_take_asset_from_asset_container": (
            lambda container_label, asset_label: _take_asset_from_asset_container(
                caller,
                str(container_label),
                str(asset_label),
            )
        ),
        "sandbox_set_asset_container_open": (
            lambda container_label, is_open: _set_asset_container_open(
                caller,
                str(container_label),
                bool(is_open),
            )
        ),
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
        "sandbox_set_mob_state": lambda mob_label, state_key, value: _set_mob_state(
            caller,
            str(mob_label),
            str(state_key),
            value,
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


def _project_location_asset_actions(
    location: SandboxLocation,
    *,
    graph: Graph,
) -> None:
    for asset_label, asset in sorted(location.assets.items()):
        asset_name = _asset_name(asset)
        if _asset_portable(asset):
            Action(
                registry=graph,
                label=f"sandbox_take_{location.get_label()}_{asset_label}",
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=f"Take {asset_name}",
                effects=[Effect(expr=f"sandbox_take_asset({asset_label!r})")],
                journal_text=_asset_take_text(asset),
                tags={"dynamic", "sandbox", "asset", "take"},
                ui_hints=_sandbox_contribution_hints(
                    location,
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
                label=f"sandbox_read_{location.get_label()}_{asset_label}",
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=f"Read {asset_name}",
                journal_text=read_text,
                tags={"dynamic", "sandbox", "asset", "read"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_asset",
                    contribution="read",
                    source_label=asset_label,
                    source_kind="asset",
                    verb="read",
                    asset=asset_label,
                ),
            )


def _project_carried_asset_actions(
    location: SandboxLocation,
    *,
    graph: Graph,
    player_assets: HasAssets,
    projection_state: SandboxProjectionState,
) -> None:
    for asset_label, asset in sorted(player_assets.assets.items()):
        asset_name = _asset_name(asset)
        if _asset_is_switchable(asset):
            lit = _asset_lit(asset)
            Action(
                registry=graph,
                label=f"sandbox_light_{location.get_label()}_{asset_label}",
                predecessor_id=location.uid,
                successor_id=location.uid,
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
                journal_text=(
                    _asset_turn_off_text(asset) if lit else _asset_turn_on_text(asset)
                ),
                tags={"dynamic", "sandbox", "asset", "light"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_asset",
                    contribution="light",
                    source_label=asset_label,
                    source_kind="asset",
                    verb="turn_off" if lit else "turn_on",
                    asset=asset_label,
                ),
            )
        if _asset_is_container(asset):
            is_open = asset.container.is_open
            Action(
                registry=graph,
                label=f"sandbox_container_toggle_{location.get_label()}_{asset_label}",
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=_asset_container_action_text(asset),
                effects=[
                    Effect(
                        expr=(
                            f"sandbox_set_asset_container_open({asset_label!r}, False)"
                            if is_open
                            else f"sandbox_set_asset_container_open({asset_label!r}, True)"
                        )
                    )
                ],
                journal_text=(
                    _asset_container_close_text(asset)
                    if is_open
                    else _asset_container_open_text(asset)
                ),
                tags={"dynamic", "sandbox", "asset", "container"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_asset",
                    contribution="container",
                    source_label=asset_label,
                    source_kind="asset",
                    verb="close" if is_open else "open",
                    asset=asset_label,
                ),
            )
        if projection_state.suppress_asset_affordances:
            continue
        Action(
            registry=graph,
            label=f"sandbox_drop_{location.get_label()}_{asset_label}",
            predecessor_id=location.uid,
            successor_id=location.uid,
            text=f"Drop {asset_name}",
            effects=[Effect(expr=f"sandbox_drop_asset({asset_label!r})")],
            journal_text=_asset_drop_text(asset),
            tags={"dynamic", "sandbox", "asset", "drop"},
            ui_hints=_sandbox_contribution_hints(
                location,
                source="sandbox_asset",
                contribution="drop",
                source_label=asset_label,
                source_kind="asset",
                verb="drop",
                asset=asset_label,
            ),
        )


def _project_fixture_container_actions(
    location: SandboxLocation,
    *,
    graph: Graph,
    player_assets: HasAssets,
) -> None:
    for fixture in location.fixtures:
        if fixture.container is None:
            continue
        for asset_label, asset in sorted(player_assets.assets.items()):
            asset_name = _asset_name(asset)
            Action(
                registry=graph,
                label=(
                    f"sandbox_put_{location.get_label()}_{asset_label}_"
                    f"in_{fixture.label}"
                ),
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=f"Put {asset_name} in {fixture.name or fixture.label}",
                availability=[
                    Predicate(
                        expr=(
                            "sandbox_fixture_can_receive_asset("
                            f"{fixture.label!r}, {asset_label!r})"
                        )
                    )
                ],
                effects=[
                    Effect(
                        expr=(
                            f"sandbox_put_asset_in_fixture({fixture.label!r}, "
                            f"{asset_label!r})"
                        )
                    )
                ],
                journal_text="Done.",
                tags={"dynamic", "sandbox", "asset", "container", "put"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_fixture",
                    contribution="put",
                    source_label=fixture.label,
                    source_kind="fixture",
                    asset=asset_label,
                    target=fixture.label,
                ),
            )
        if not fixture.container_accessible():
            continue
        for asset_label, asset in sorted(fixture.assets.items()):
            asset_name = _asset_name(asset)
            Action(
                registry=graph,
                label=(
                    f"sandbox_take_{location.get_label()}_{asset_label}_"
                    f"from_{fixture.label}"
                ),
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=f"Take {asset_name} from {fixture.name or fixture.label}",
                effects=[
                    Effect(
                        expr=(
                            f"sandbox_take_asset_from_fixture({fixture.label!r}, "
                            f"{asset_label!r})"
                        )
                    )
                ],
                journal_text=_asset_take_text(asset),
                tags={"dynamic", "sandbox", "asset", "container", "take"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_fixture",
                    contribution="take_from_container",
                    source_label=fixture.label,
                    source_kind="fixture",
                    asset=asset_label,
                    target=fixture.label,
                ),
            )


def _project_asset_container_actions(
    location: SandboxLocation,
    *,
    graph: Graph,
    player_assets: HasAssets,
) -> None:
    for container_label, container_asset in sorted(player_assets.assets.items()):
        container = container_asset.container
        if container is None:
            continue
        for asset_label, asset in sorted(player_assets.assets.items()):
            if asset_label == container_label:
                continue
            asset_name = _asset_name(asset)
            container_name = _asset_name(container_asset)
            Action(
                registry=graph,
                label=(
                    f"sandbox_put_{location.get_label()}_{asset_label}_"
                    f"in_{container_label}"
                ),
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=f"Put {asset_name} in {container_name}",
                availability=[
                    Predicate(
                        expr=(
                            "sandbox_asset_container_can_receive("
                            f"{container_label!r}, {asset_label!r})"
                        )
                    )
                ],
                effects=[
                    Effect(
                        expr=(
                            "sandbox_put_asset_in_asset_container("
                            f"{container_label!r}, {asset_label!r})"
                        )
                    )
                ],
                journal_text="Done.",
                tags={"dynamic", "sandbox", "asset", "container", "put"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_asset",
                    contribution="put",
                    source_label=container_label,
                    source_kind="asset",
                    asset=asset_label,
                    target=container_label,
                ),
            )
        if not container.is_open:
            continue
        for asset_label, asset in sorted(container.assets.items()):
            asset_name = _asset_name(asset)
            container_name = _asset_name(container_asset)
            Action(
                registry=graph,
                label=(
                    f"sandbox_take_{location.get_label()}_{asset_label}_"
                    f"from_{container_label}"
                ),
                predecessor_id=location.uid,
                successor_id=location.uid,
                text=f"Take {asset_name} from {container_name}",
                effects=[
                    Effect(
                        expr=(
                            "sandbox_take_asset_from_asset_container("
                            f"{container_label!r}, {asset_label!r})"
                        )
                    )
                ],
                journal_text=_asset_take_text(asset),
                tags={"dynamic", "sandbox", "asset", "container", "take"},
                ui_hints=_sandbox_contribution_hints(
                    location,
                    source="sandbox_asset",
                    contribution="take_from_container",
                    source_label=container_label,
                    source_kind="asset",
                    asset=asset_label,
                    target=container_label,
                ),
            )


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
        _project_location_asset_actions(caller, graph=graph)

    player_assets = _player_asset_holder(caller)
    if player_assets is None:
        return None
    _project_carried_asset_actions(
        caller,
        graph=graph,
        player_assets=player_assets,
        projection_state=projection_state,
    )
    if projection_state.suppress_asset_affordances:
        return None

    _project_fixture_container_actions(caller, graph=graph, player_assets=player_assets)
    _project_asset_container_actions(caller, graph=graph, player_assets=player_assets)
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

    for fixture in caller.fixtures:
        if not fixture.lockable or not fixture.locked:
            continue
        Action(
            registry=graph,
            label=f"sandbox_unlock_{caller.get_label()}_{fixture.label}",
            predecessor_id=caller.uid,
            successor_id=caller.uid,
            text=fixture.action_text(),
            availability=[
                Predicate(expr=f"sandbox_fixture_can_unlock({fixture.label!r})")
            ],
            effects=[Effect(expr=f"_s.unlock_fixture({fixture.label!r})")],
            journal_text=fixture.unlock_text,
            tags={"dynamic", "sandbox", "unlock"},
            ui_hints=_sandbox_contribution_hints(
                caller,
                source="sandbox_fixture",
                contribution="unlock",
                source_label=fixture.label,
                source_kind="fixture",
                target=fixture.label,
                key=fixture.key,
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

    for fixture in caller.fixtures:
        if fixture.openable is None:
            continue
        if fixture.open:
            Action(
                registry=graph,
                label=f"sandbox_close_{caller.get_label()}_{fixture.label}",
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=fixture.close_text_label(),
                availability=[
                    Predicate(expr=f"sandbox_fixture_can_close({fixture.label!r})")
                ],
                effects=[Effect(expr=f"_s.close_fixture({fixture.label!r})")],
                journal_text=fixture.close_text,
                tags={"dynamic", "sandbox", "fixture", "close"},
                ui_hints=_sandbox_contribution_hints(
                    caller,
                    source="sandbox_fixture",
                    contribution="close",
                    source_label=fixture.label,
                    source_kind="fixture",
                    target=fixture.label,
                ),
            )
            continue
        Action(
            registry=graph,
            label=f"sandbox_open_{caller.get_label()}_{fixture.label}",
            predecessor_id=caller.uid,
            successor_id=caller.uid,
            text=fixture.open_text_label(),
            availability=[Predicate(expr=f"sandbox_fixture_can_open({fixture.label!r})")],
            effects=[Effect(expr=f"_s.open_fixture({fixture.label!r})")],
            journal_text=fixture.open_text,
            tags={"dynamic", "sandbox", "fixture", "open"},
            ui_hints=_sandbox_contribution_hints(
                caller,
                source="sandbox_fixture",
                contribution="open",
                source_label=fixture.label,
                source_kind="fixture",
                target=fixture.label,
            ),
        )
    return None


@on_provision(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
)
def project_sandbox_mob_actions(*, caller, ctx, **_kw):
    """Project present mob affordances into ordinary sandbox actions."""
    if not isinstance(caller, SandboxLocation):
        return None
    if not caller.auto_provision:
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="mob", ctx=ctx)
    if _projection_state(caller, ctx).suppress_location_description:
        return None

    for mob in _present_mobs(caller):
        mob_label = mob.get_label()
        for affordance in mob.affordances:
            affordance_tag = _mob_affordance_tag(affordance.label)
            if affordance_tag is None:
                continue
            effects = [
                Effect(
                    expr=(
                        f"sandbox_set_mob_state({mob_label!r}, "
                        f"{state_key!r}, {state_value!r})"
                    )
                )
                for state_key, state_value in affordance.state_effects.items()
            ]
            Action(
                registry=graph,
                label=(
                    f"sandbox_mob_{caller.get_label()}_{mob_label}_"
                    f"{affordance.label}"
                ),
                predecessor_id=caller.uid,
                successor_id=caller.uid,
                text=affordance.text,
                effects=effects,
                journal_text=affordance.journal_text,
                tags={"dynamic", "sandbox", "mob", affordance_tag},
                ui_hints=_sandbox_contribution_hints(
                    caller,
                    source="sandbox_mob",
                    contribution="mob",
                    source_label=mob_label,
                    source_kind="mob",
                    mob=mob_label,
                    action=affordance.label,
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
    if not caller.auto_provision or not _nearest_wait_enabled(caller):
        return None
    graph = getattr(caller, "graph", None)
    if graph is None or bool(getattr(graph, "frozen_shape", False)):
        return None

    _clear_dynamic_sandbox_actions(caller, action_kind="wait", ctx=ctx)

    wait_text = _nearest_wait_text(caller)
    turn_delta = _nearest_wait_turn_delta(caller)
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
            and fragment.source_id == caller.uid
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


@on_compose_journal(
    wants_caller_kind=SandboxLocation,
    wants_exact_kind=False,
    priority=Priority.NORMAL,
)
def compose_sandbox_mob_journal(*, caller, ctx, fragments, **_kw):
    """Append visible present-mob journal fragments to sandbox locations."""
    if not isinstance(caller, SandboxLocation):
        return None
    if _projection_state(caller, ctx).suppress_location_description:
        return None

    additions = [
        ContentFragment(content=mob.present_text, source_id=mob.uid)
        for mob in _present_mobs(caller)
        if mob.present_text
    ]
    if not additions:
        return None
    return [*fragments, *additions]
