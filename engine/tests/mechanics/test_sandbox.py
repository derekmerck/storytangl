"""Sandbox mechanic contracts for dynamic scene-location hubs."""

from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Graph, Selector, Token
from tangl.core.runtime_op import Effect, Predicate
from tangl.mechanics.sandbox import (
    SandboxExit,
    SandboxLocation,
    SandboxLockable,
    SandboxScope,
    SandboxVisibilityRule,
    Schedule,
    ScheduleEntry,
    ScheduledEvent,
    ScheduledPresence,
    WorldTime,
    advance_world_turn,
    current_world_time,
    normalize_sandbox_direction,
)
from tangl.story import Action, Block, StoryGraph
from tangl.story.concepts import Actor, Role
from tangl.story.concepts.asset import AssetType
from tangl.story.fragments import ChoiceFragment, ContentFragment
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Ledger, Requirement
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


class SandboxItemType(AssetType):
    name: str = ""
    portable: bool = True
    readable: bool = False
    read_text: str | None = None
    light_source: bool = False
    lit: bool = Field(default=False, json_schema_extra={"instance_var": True})
    turn_on_text: str | None = None
    turn_off_text: str | None = None
    take_text: str | None = None
    drop_text: str | None = None


@pytest.fixture(autouse=True)
def _clear_sandbox_item_types() -> None:
    SandboxItemType.clear_instances()
    yield
    SandboxItemType.clear_instances()


def _sandbox_graph() -> tuple[Graph, SandboxLocation, SandboxLocation, SandboxLocation]:
    graph = Graph(label="tiny_cave")
    road = SandboxLocation(
        label="road",
        location_name="Road",
        sandbox_scope="tiny_cave",
        links={"east": "building", "west": "cave_entrance"},
    )
    building = SandboxLocation(
        label="building",
        location_name="Building",
        sandbox_scope="tiny_cave",
        links={"west": "road"},
    )
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        sandbox_scope="tiny_cave",
        links={"east": "road"},
    )
    graph.add(road)
    graph.add(building)
    graph.add(cave_entrance)
    return graph, road, building, cave_entrance


def _dynamic_sandbox_actions(location: SandboxLocation) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox", "movement"}.issubset(edge.tags)
    ]


def _dynamic_sandbox_actions_with_tag(location: SandboxLocation, tag: str) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox", tag}.issubset(edge.tags)
    ]


def test_world_time_is_derived_from_world_turn() -> None:
    assert WorldTime.from_turn(0).model_dump() == {
        "turn": 0,
        "period": 1,
        "day": 1,
        "day_of_month": 1,
        "month": 1,
        "season": 1,
        "year": 1,
    }

    later = WorldTime.from_turn(4 * 28 * 3)

    assert later.period == 1
    assert later.day_of_month == 1
    assert later.month == 4
    assert later.season == 2
    assert later.year == 1


def test_world_turn_helpers_use_mutable_locals() -> None:
    location = SandboxLocation(label="road", locals={"world_turn": 1})

    assert current_world_time(location).turn == 1
    assert advance_world_turn(location, 2) == 3
    assert location.locals["world_turn"] == 3


def test_schedule_matches_time_location_and_presence() -> None:
    schedule = Schedule(
        entries=[
            ScheduleEntry(label="traveler", location="road", actor="traveler", period=3),
            ScheduleEntry(label="merchant", location="building", period=3),
        ]
    )
    world_time = WorldTime.from_turn(2)

    matches = schedule.matching(
        world_time,
        location="road",
        actors_present=["traveler"],
    )

    assert [entry.label for entry in matches] == ["traveler"]


def test_sandbox_location_links_project_normal_actions() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Go east to Building",
        "Go west to Cave Entrance",
    }
    assert all(action.successor is not None for action in actions)
    assert all(action.ui_hints["source"] == "sandbox_link" for action in actions)
    assert all(action.ui_hints["contribution"] == "movement" for action in actions)
    assert all(action.ui_hints["source_kind"] == "location" for action in actions)
    assert all(action.ui_hints["source_label"] == "road" for action in actions)
    assert all(action.ui_hints["scope"] == "tiny_cave" for action in actions)


def test_sandbox_location_links_normalize_direction_aliases() -> None:
    assert normalize_sandbox_direction("n") == "north"
    assert normalize_sandbox_direction("U") == "up"
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.links = {"n": "building", "u": "cave_entrance"}
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Go north to Building",
        "Go up to Cave Entrance",
    }
    hints = {action.ui_hints["raw_direction"]: action.ui_hints["direction"] for action in actions}
    assert hints == {"n": "north", "u": "up"}


def test_sandbox_structured_exit_can_override_choice_text() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.links = {
        "in": SandboxExit(target="building", text="Enter the building"),
        "out": {"target": "cave_entrance", "text": "Leave for the cave"},
    }
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {
        "Enter the building",
        "Leave for the cave",
    }


def test_manual_location_action_suppresses_generated_link_choice() -> None:
    graph, road, building, _cave_entrance = _sandbox_graph()
    Action(
        registry=graph,
        label="manual_enter_building",
        predecessor_id=road.uid,
        successor_id=building.uid,
        text="Step inside",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {"Go west to Cave Entrance"}


def test_sandbox_movement_refresh_removes_stale_actions() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)
    first_ids = {action.uid for action in _dynamic_sandbox_actions(road)}

    road.links = {"east": "building"}
    do_provision(road, ctx=ctx)

    actions = _dynamic_sandbox_actions(road)
    assert {action.text for action in actions} == {"Go east to Building"}
    assert first_ids.isdisjoint({action.uid for action in actions})


def test_target_location_availability_gates_generated_movement_choice() -> None:
    graph, road, _building, cave_entrance = _sandbox_graph()
    cave_entrance.availability = [Predicate(expr="grate_open and lamp_lit")]
    cave_entrance.locals.update({"grate_open": True, "lamp_lit": False})
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)

    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    west = next(choice for choice in choices if choice.text == "Go west to Cave Entrance")

    assert west.available is False
    assert west.unavailable_reason == "guard_failed_or_unavailable"

    cave_entrance.locals["lamp_lit"] = True
    ctx._ns_cache.clear()
    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    west = next(choice for choice in choices if choice.text == "Go west to Cave Entrance")

    assert west.available is True


def test_sandbox_location_projects_wait_choice() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.locals["world_turn"] = 0
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)

    waits = _dynamic_sandbox_actions_with_tag(road, "wait")
    assert len(waits) == 1
    assert waits[0].text == "Wait"
    assert waits[0].successor is road
    assert waits[0].payload == {"sandbox_action": "wait", "turn_delta": 1}


def test_wait_choice_advances_world_turn_through_ledger() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    road.locals["world_turn"] = 0
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)
    wait = _dynamic_sandbox_actions_with_tag(road, "wait")[0]
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    ledger.resolve_choice(wait.uid, choice_payload=wait.payload)

    assert ledger.cursor is road
    assert road.locals["world_turn"] == 1


def test_scheduled_event_projects_only_at_matching_location_and_time() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(traveler)
    road.locals["world_turn"] = 1
    road.scheduled_events = [
        ScheduledEvent(
            label="traveler",
            location="road",
            period=3,
            target="traveler_arrives",
            text="Talk to traveler",
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []

    road.locals["world_turn"] = 2
    ctx._ns_cache.clear()
    do_provision(road, ctx=ctx)
    events = _dynamic_sandbox_actions_with_tag(road, "event")

    assert len(events) == 1
    assert events[0].text == "Talk to traveler"
    assert events[0].successor is traveler


def test_scheduled_event_renders_as_normal_choice_fragment() -> None:
    graph, road, _building, _cave_entrance = _sandbox_graph()
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(traveler)
    road.locals["world_turn"] = 2
    road.scheduled_events = [
        ScheduledEvent(
            label="traveler",
            location="road",
            period=3,
            target="traveler_arrives",
            text="Talk to traveler",
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)

    fragments = render_block_choices(caller=road, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]

    assert any(choice.text == "Talk to traveler" and choice.available for choice in choices)


def test_locked_local_object_projects_unavailable_unlock_without_key() -> None:
    graph, _road, _building, cave_entrance = _sandbox_graph()
    cave_entrance.lockables = [
        SandboxLockable(
            label="grate",
            name="grate",
            key="keys",
            unlock_text="The key turns with a click. The grate unlocks.",
        )
    ]
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)

    do_provision(cave_entrance, ctx=ctx)

    unlocks = _dynamic_sandbox_actions_with_tag(cave_entrance, "unlock")
    assert [action.text for action in unlocks] == ["Unlock grate"]
    assert unlocks[0].successor is cave_entrance
    assert unlocks[0].journal_text == "The key turns with a click. The grate unlocks."

    fragments = render_block_choices(caller=cave_entrance, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    unlock = next(choice for choice in choices if choice.text == "Unlock grate")
    assert unlock.available is False
    assert unlock.unavailable_reason == "guard_failed_or_unavailable"


def test_locked_local_object_unlocks_with_carried_key_and_stops_projecting() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        content="The grate is {grate_state}.",
        locals={"grate_state": "locked"},
        lockables=[
            SandboxLockable(
                label="grate",
                name="grate",
                key="keys",
                unlock_text="The key turns with a click. The grate unlocks.",
            )
        ],
    )
    SandboxItemType(label="keys", name="keys")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    scope.player_assets.add_asset(keys)
    graph.add(scope)
    graph.add(cave_entrance)
    graph.add(keys)
    scope.add_child(cave_entrance)
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)
    do_provision(cave_entrance, ctx=ctx)
    unlock = _dynamic_sandbox_actions_with_tag(cave_entrance, "unlock")[0]
    unlock.effects.append(Effect(expr="grate_state = 'unlocked'"))
    ledger = Ledger.from_graph(graph, entry_id=cave_entrance.uid)

    ledger.resolve_choice(unlock.uid)

    assert cave_entrance.lockables[0].locked is False
    assert cave_entrance.locals["grate_state"] == "unlocked"
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content[:2] == [
        "The key turns with a click. The grate unlocks.",
        "The grate is unlocked.",
    ]

    do_provision(cave_entrance, ctx=PhaseCtx(graph=graph, cursor_id=cave_entrance.uid))
    assert _dynamic_sandbox_actions_with_tag(cave_entrance, "unlock") == []


def test_locked_local_object_unlocks_with_key_asset_in_player_inventory() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    cave_entrance = SandboxLocation(
        label="cave_entrance",
        location_name="Cave Entrance",
        lockables=[
            SandboxLockable(
                label="grate",
                name="grate",
                key="keys",
                unlock_text="The key turns with a click. The grate unlocks.",
            )
        ],
    )
    SandboxItemType(label="keys", name="keys")
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    scope.player_assets.add_asset(keys)
    graph.add(scope)
    graph.add(cave_entrance)
    graph.add(keys)
    scope.add_child(cave_entrance)
    ctx = PhaseCtx(graph=graph, cursor_id=cave_entrance.uid)

    do_provision(cave_entrance, ctx=ctx)
    fragments = render_block_choices(caller=cave_entrance, ctx=ctx)
    choices = [fragment for fragment in fragments or [] if isinstance(fragment, ChoiceFragment)]
    unlock = next(choice for choice in choices if choice.text == "Unlock grate")

    assert unlock.available is True


def test_location_assets_project_take_read_and_drop_actions() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope")
    building = SandboxLocation(label="building", location_name="Building")
    SandboxItemType(label="keys", name="keys")
    SandboxItemType(
        label="leaflet",
        name="leaflet",
        readable=True,
        read_text="Welcome to Adventure!",
    )
    keys = Token[SandboxItemType](token_from="keys", label="keys")
    leaflet = Token[SandboxItemType](token_from="leaflet", label="leaflet")
    building.add_asset(keys)
    building.add_asset(leaflet)
    graph.add(scope)
    graph.add(building)
    graph.add(keys)
    graph.add(leaflet)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=building.uid)

    do_provision(building, ctx=ctx)
    assets = _dynamic_sandbox_actions_with_tag(building, "asset")

    assert {action.text for action in assets} == {
        "Read leaflet",
        "Take keys",
        "Take leaflet",
    }
    read = next(action for action in assets if action.text == "Read leaflet")
    assert read.journal_text == "Welcome to Adventure!"

    take_keys = next(action for action in assets if action.text == "Take keys")
    ledger = Ledger.from_graph(graph, entry_id=building.uid)
    ledger.resolve_choice(take_keys.uid)

    assert not building.has_asset("keys")
    assert scope.player_assets.has_asset("keys")

    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))
    drop_keys = next(
        action
        for action in _dynamic_sandbox_actions_with_tag(building, "asset")
        if action.text == "Drop keys"
    )
    ledger.resolve_choice(drop_keys.uid)

    assert building.has_asset("keys")
    assert not scope.player_assets.has_asset("keys")


def test_darkness_rule_substitutes_journal_and_suppresses_local_asset_actions() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(
        label="dark_cave",
        location_name="Dark Cave",
        content="A glittering nugget rests here.",
    )
    start = Block(label="start", content="Begin.")
    SandboxItemType(label="nugget", name="nugget")
    nugget = Token[SandboxItemType](token_from="nugget", label="nugget")
    cave.add_asset(nugget)
    graph.add(scope)
    graph.add(start)
    graph.add(cave)
    graph.add(nugget)
    scope.add_child(cave)
    enter_cave = Action(
        registry=graph,
        label="enter_cave",
        predecessor_id=start.uid,
        successor_id=cave.uid,
        text="Enter cave",
    )
    ctx = PhaseCtx(graph=graph, cursor_id=cave.uid)

    do_provision(cave, ctx=ctx)
    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.resolve_choice(enter_cave.uid)

    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content == ["It is now pitch dark."]
    assert _dynamic_sandbox_actions_with_tag(cave, "asset") == []


def test_carried_lamp_restores_dark_location_detail_and_asset_affordances() -> None:
    graph = StoryGraph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        visibility_rules=[
            SandboxVisibilityRule(journal_text="It is now pitch dark.")
        ],
    )
    cave = SandboxLocation(
        label="dark_cave",
        location_name="Dark Cave",
        content="A glittering nugget rests here.",
    )
    SandboxItemType(
        label="lamp",
        name="lamp",
        light_source=True,
        turn_on_text="Your lamp is now on.",
    )
    SandboxItemType(label="nugget", name="nugget")
    lamp = Token[SandboxItemType](token_from="lamp", label="lamp")
    nugget = Token[SandboxItemType](token_from="nugget", label="nugget")
    scope.player_assets.add_asset(lamp)
    cave.add_asset(nugget)
    graph.add(scope)
    graph.add(cave)
    graph.add(lamp)
    graph.add(nugget)
    scope.add_child(cave)
    ctx = PhaseCtx(graph=graph, cursor_id=cave.uid)

    do_provision(cave, ctx=ctx)
    dark_actions = _dynamic_sandbox_actions_with_tag(cave, "asset")
    assert [action.text for action in dark_actions] == ["Turn on lamp"]

    turn_on = dark_actions[0]
    ledger = Ledger(graph=graph, cursor_id=cave.uid)
    ledger.resolve_choice(turn_on.uid)

    assert lamp.lit is True
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert content[:2] == ["Your lamp is now on.", "A glittering nugget rests here."]

    do_provision(cave, ctx=PhaseCtx(graph=graph, cursor_id=cave.uid))
    lit_actions = _dynamic_sandbox_actions_with_tag(cave, "asset")
    assert {action.text for action in lit_actions} == {
        "Drop lamp",
        "Take nugget",
        "Turn off lamp",
    }


def test_scope_donates_wait_to_child_locations() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        wait_text="Pass time",
        wait_turn_delta=2,
        locals={"world_turn": 0},
    )
    road = SandboxLocation(label="road", location_name="Road")
    peer = SandboxLocation(label="peer", location_name="Peer", wait_enabled=False)
    graph.add(scope)
    graph.add(road)
    graph.add(peer)
    scope.add_child(road)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    wait = _dynamic_sandbox_actions_with_tag(road, "wait")[0]

    assert wait.text == "Pass time"
    assert wait.payload == {"sandbox_action": "wait", "turn_delta": 2}

    do_provision(peer, ctx=PhaseCtx(graph=graph, cursor_id=peer.uid))
    assert _dynamic_sandbox_actions_with_tag(peer, "wait") == []


def test_scope_wait_advances_shared_scope_time() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(label="tiny_cave_scope", wait_turn_delta=2, locals={"world_turn": 0})
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    scope.add_child(road)
    scope.add_child(building)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)
    do_provision(road, ctx=ctx)
    wait = _dynamic_sandbox_actions_with_tag(road, "wait")[0]
    ledger = Ledger.from_graph(graph, entry_id=road.uid)

    ledger.resolve_choice(wait.uid, choice_payload=wait.payload)

    assert scope.locals["world_turn"] == 2
    assert current_world_time(building).turn == 2
    assert "world_turn" not in road.locals


def test_scope_scheduled_event_is_donated_to_matching_child_location() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 2},
        scheduled_events=[
            ScheduledEvent(
                label="traveler",
                location="road",
                period=3,
                target="traveler_arrives",
                text="Talk to traveler",
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road")
    building = SandboxLocation(label="building", location_name="Building")
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(scope)
    graph.add(road)
    graph.add(building)
    graph.add(traveler)
    scope.add_child(road)
    scope.add_child(building)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))

    road_events = _dynamic_sandbox_actions_with_tag(road, "event")
    building_events = _dynamic_sandbox_actions_with_tag(building, "event")
    assert [event.text for event in road_events] == ["Talk to traveler"]
    assert building_events == []


def test_scope_once_event_triggers_on_entry_returns_and_suppresses_after_target_visit() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        scheduled_events=[
            ScheduledEvent(
                label="first_entry",
                target="orientation",
                text="Take in your surroundings",
                activation="first",
                once=True,
                return_to_location=True,
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road", links={"east": "building"})
    building = SandboxLocation(label="building", location_name="Building", links={"west": "road"})
    cave_entrance = SandboxLocation(label="cave_entrance", location_name="Cave Entrance")
    inside_cave = SandboxLocation(label="inside_cave", location_name="Inside Cave")
    start = Block(label="start", content="Begin.")
    orientation = Block(label="orientation", content="You get your bearings.")
    graph.add(scope)
    graph.add(start)
    graph.add(road)
    graph.add(building)
    graph.add(cave_entrance)
    graph.add(inside_cave)
    graph.add(orientation)
    scope.add_child(road)
    scope.add_child(building)
    scope.add_child(cave_entrance)
    scope.add_child(inside_cave)
    enter_road = Action(
        registry=graph,
        label="enter_road",
        predecessor_id=start.uid,
        successor_id=road.uid,
        text="Enter sandbox",
    )

    ledger = Ledger.from_graph(graph, entry_id=start.uid)
    ledger.resolve_choice(enter_road.uid)

    assert ledger.cursor is road
    assert orientation.locals["_visited"] is True
    assert road.locals["_visited"] is True

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []

    do_provision(building, ctx=PhaseCtx(graph=graph, cursor_id=building.uid))
    assert _dynamic_sandbox_actions_with_tag(building, "event") == []


def test_scope_presence_can_gate_scheduled_events() -> None:
    graph = Graph(label="tiny_cave")
    scope = SandboxScope(
        label="tiny_cave_scope",
        locals={"world_turn": 2},
        scheduled_presence=[
            ScheduledPresence(
                label="traveler_presence",
                actor="traveler",
                location="road",
                period=3,
            )
        ],
        scheduled_events=[
            ScheduledEvent(
                label="traveler_chat",
                actor="traveler",
                location="road",
                period=3,
                target="traveler_arrives",
                text="Talk to traveler",
            )
        ],
    )
    road = SandboxLocation(label="road", location_name="Road")
    traveler = Block(label="traveler_arrives", content="A traveler waves from the road.")
    graph.add(scope)
    graph.add(road)
    graph.add(traveler)
    scope.add_child(road)
    ctx = PhaseCtx(graph=graph, cursor_id=road.uid)

    do_provision(road, ctx=ctx)
    assert [event.text for event in _dynamic_sandbox_actions_with_tag(road, "event")] == [
        "Talk to traveler"
    ]

    scope.scheduled_presence = []
    do_provision(road, ctx=ctx)
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []


def test_role_provider_can_donate_sandbox_events() -> None:
    class HelpfulActor(Actor):
        def get_sandbox_events(self, *, caller, ctx, ns):
            if not ns.get("can_pause", True):
                return []
            return [
                ScheduledEvent(
                    label="repair_armor",
                    target="armor_repair",
                    text=f"Ask {self.name} to fix your armor",
                    return_to_location=True,
                )
            ]

    graph = Graph(label="barn_dance")
    scope = SandboxScope(label="barn_dance_scope")
    road = SandboxLocation(label="dance_floor", location_name="Dance Floor")
    repair = Block(label="armor_repair", content="Aria tightens the straps.")
    aria = HelpfulActor(label="aria", name="Aria")
    role = Role(
        label="friend",
        predecessor_id=scope.uid,
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )
    graph.add(scope)
    graph.add(road)
    graph.add(repair)
    graph.add(aria)
    graph.add(role)
    scope.add_child(road)
    role.set_provider(aria)

    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    events = _dynamic_sandbox_actions_with_tag(road, "event")

    assert [event.text for event in events] == ["Ask Aria to fix your armor"]
    assert events[0].successor is repair
    assert events[0].return_phase is not None

    road.locals["can_pause"] = False
    do_provision(road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid))
    assert _dynamic_sandbox_actions_with_tag(road, "event") == []
