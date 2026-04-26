"""Sandbox mechanic contracts for dynamic scene-location hubs."""

from __future__ import annotations

from tangl.core import Graph, Selector
from tangl.core.runtime_op import Predicate
from tangl.mechanics.sandbox import (
    SandboxLocation,
    SandboxScope,
    Schedule,
    ScheduleEntry,
    ScheduledEvent,
    ScheduledPresence,
    WorldTime,
    advance_world_turn,
    current_world_time,
)
from tangl.story import Action, Block
from tangl.story.concepts import Actor, Role
from tangl.story.fragments import ChoiceFragment
from tangl.story.system_handlers import render_block_choices
from tangl.vm import Ledger, Requirement
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


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
        if {"dynamic", "sandbox", "movement"}.issubset(getattr(edge, "tags", set()) or set())
    ]


def _dynamic_sandbox_actions_with_tag(location: SandboxLocation, tag: str) -> list[Action]:
    return [
        edge
        for edge in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox", tag}.issubset(getattr(edge, "tags", set()) or set())
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
