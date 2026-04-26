"""Sandbox mechanic contracts for dynamic scene-location hubs."""

from __future__ import annotations

from tangl.core import Graph, Selector
from tangl.core.runtime_op import Predicate
from tangl.mechanics.sandbox import (
    SandboxLocation,
    Schedule,
    ScheduleEntry,
    WorldTime,
    advance_world_turn,
    current_world_time,
)
from tangl.story import Action
from tangl.story.fragments import ChoiceFragment
from tangl.story.system_handlers import render_block_choices
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
        for edge in location.edges_out(Selector(has_kind=Action, trigger_phase=None))
        if {"dynamic", "sandbox", "movement"}.issubset(getattr(edge, "tags", set()) or set())
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
