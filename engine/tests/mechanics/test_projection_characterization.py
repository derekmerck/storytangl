"""Characterization (golden) tests for dynamic-action projection shape.

Executable form of the filled audit table in
``docs/src/design/planning/AFFORDANCE_MODEL.md`` ("The audit table (filled)").
Each test docstring cites its audit-table row by mechanism name so the table
and the tests share row identity (issue #268 synthesis item B; refs #255,
PR #274). #271 pinned the wire layer (DTO round-trips, choice payload
contracts); this module pins the layer #271 did not: VM/story-side projection
shape — labels, tags, ui_hints, payload, accepts, admission vs live
availability, phases, and cleanup behavior.

These tests RECORD the current differences between the projector families.
They must NOT be read as a uniformity contract: where families differ (game
actions wear the ``fanout`` tag without touching fanout machinery; sandbox
carries six-plus provenance-ish fields in ``ui_hints`` while menu and game
carry only the single ``source`` lifecycle token added by synthesis item D;
incremental's hand-rolled hints bypass ``_sandbox_contribution_hints`` and so
lack ``scope``), the difference is the pinned expectation. A future convergence
PR must consciously update both the audit table and the matching test here.

Cleanup vocabulary: the per-family discriminator tag sets are **mutually
non-subsuming** (a subset antichain — families intentionally share tags like
``dynamic``), NOT set-disjoint. The antichain itself is pinned by
``test_sandbox_architecture.py``; this module pins each family's observable
cleanup behavior (re-projection does not duplicate; removing the source
concept clears its edges and only its edges).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tangl.core import Graph, Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.mechanics.games import (
    GamePhase,
    HasGame,
    IncrementalGame,
    IncrementalGameHandler,
    TaskSpec,
)
from tangl.mechanics.games.handlers import provision_game_moves
from tangl.mechanics.games.rps_game import RpsGame, RpsGameHandler, RpsMove
from tangl.mechanics.sandbox import (
    SandboxCompiledAssetType,
    SandboxLocation,
    SandboxScope,
    SandboxSliceCompiler,
)

# The incremental projector registers its handlers on module import; without
# this import, hosted games are discovered but never project.
from tangl.mechanics.sandbox import incremental as sandbox_incremental
from tangl.mechanics.sandbox.handlers import (
    project_sandbox_fixture_actions,
    project_sandbox_scheduled_events,
)
from tangl.mechanics.sandbox.time import SandboxTimeCost
from tangl.story import Action, Block, InitMode, World
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.dispatch import do_provision
from tangl.vm.runtime.frame import PhaseCtx


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers and fixtures
# ─────────────────────────────────────────────────────────────────────────────

CHARACTERIZATION_SLICE: dict[str, Any] = {
    "id": "projection_characterization_slice",
    "scope": {
        "id": "char_scope",
        "scheduled_events": {
            "dawn": {
                "target": "road",
                "text": "Notice the dawn",
                "period": 1,
            }
        },
    },
    "locations": {
        "road": {
            "name": "Road",
            "traits": ["light"],
            "descriptions": {"look": "You are on the road."},
            "exits": {"east": "cave"},
        },
        "cave": {
            "name": "Cave",
            "traits": ["light"],
            "descriptions": {"look": "You are in the cave."},
            "exits": {"west": "road"},
        },
    },
    "fixtures": {
        "altar": {
            "name": "Altar",
            "initial": {"locations": ["road"]},
            "contributes": {
                "interactions": {
                    "pray": {
                        "text": "Pray at the altar",
                        "target": "current",
                        "journal": "A hush settles over the road.",
                        "availability": "True",
                        "effects": "prayed = True",
                    }
                }
            },
        }
    },
    "mobs": {
        "guide": {
            "name": "Guide",
            "initial": {"location": "cave"},
            "contributes": {
                "interactions": {
                    "ask": {
                        "text": "Ask the guide about the cave",
                        "target": "road",
                        "return_to_location": True,
                    }
                }
            },
        }
    },
}


class _ColonyGame(IncrementalGame):
    """Tiny resource-allocation shell for incremental characterization."""

    starting_resources: dict[str, int] = {"food": 1}
    starting_workers: int = 1
    task_specs: dict[str, TaskSpec] = {"forage": TaskSpec(produces={"food": 2})}
    upkeep: dict[str, int] = {"food": 1}
    unlocked_tasks: list[str] = ["forage"]


class _ColonyBlock(HasGame, Block):
    _game_class = _ColonyGame
    _game_handler_class = IncrementalGameHandler


class _RpsBlock(HasGame, Block):
    _game_class = RpsGame
    _game_handler_class = RpsGameHandler


@pytest.fixture(autouse=True)
def _clear_compiled_asset_types() -> None:
    SandboxCompiledAssetType.clear_instances()
    yield
    SandboxCompiledAssetType.clear_instances()


def _provision(node, graph) -> None:
    """Run one PLANNING projection pass with a fresh ctx (no stale ns cache)."""
    do_provision(node, ctx=PhaseCtx(graph=graph, cursor_id=node.uid))


def _dynamic_actions(node, *discriminator: str) -> list[Action]:
    return [
        edge
        for edge in node.edges_out(Selector(has_kind=Action))
        if set(discriminator).issubset(edge.tags or set())
    ]


def _hints(action: Action) -> dict[str, Any] | None:
    """Sparse ui_hints dict (unset model defaults dropped); None when unset."""
    if action.ui_hints is None:
        return None
    return {
        key: value
        for key, value in action.ui_hints.model_dump().items()
        if value is not None and value != []
    }


def _availability_exprs(action: Action) -> list[str]:
    return [predicate.expr for predicate in action.availability]


def _effect_exprs(action: Action) -> list[str]:
    return [effect.expr for effect in action.effects]


# ─────────────────────────────────────────────────────────────────────────────
# Row: Menu fanout
# ─────────────────────────────────────────────────────────────────────────────


def _menu_script() -> dict[str, Any]:
    return {
        "label": "menu_characterization",
        "metadata": {"start_at": "lab.start"},
        "scenes": {
            "lab": {
                "blocks": [
                    {
                        "label": "start",
                        "content": "Start",
                        "actions": [{"text": "Enter hub", "successor": "hub"}],
                    },
                    {
                        "label": "hub",
                        "kind": "MenuBlock",
                        "content": "What should we do?",
                        "menu_items": {
                            "has_tags": ["activity"],
                            "return_when_done": True,
                        },
                    },
                    {
                        "label": "aria",
                        "tags": ["activity"],
                        "locals": {"action_text": "Listen to Aria"},
                        "content": "Aria tunes her harp.",
                    },
                    {
                        "label": "brew",
                        "tags": ["activity"],
                        "action_name": "Brew tea",
                        "content": "The kettle is ready.",
                    },
                ]
            }
        },
    }


def _enter_menu_hub() -> tuple[Graph, Block]:
    result = World.from_script_data(script_data=_menu_script()).create_story(
        "menu_characterization",
        init_mode=InitMode.EAGER,
    )
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    enter = next(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    ledger.resolve_choice(enter.uid)
    return result.graph, ledger.cursor


def test_menu_fanout_action_shape() -> None:
    """Audit-table row: "Menu fanout".

    The reference path — the only consumer of real ``Fanout`` machinery. Since
    synthesis item D it carries the single ``source`` lifecycle token (the
    minimal cleanup-attribution added so menu is as explainable as sandbox),
    but still no other hints, no payload, and a positional (index-derived)
    label instead of a source-derived one.
    """
    _, hub = _enter_menu_hub()

    actions = _dynamic_actions(hub, "dynamic", "fanout", "menu")

    assert sorted(action.label for action in actions) == ["menu_hub_0", "menu_hub_1"]
    assert {action.text for action in actions} == {"Listen to Aria", "Brew tea"}
    for action in actions:
        assert action.tags == {"dynamic", "fanout", "menu"}
        # Item D minimal attribution: one lifecycle token, in the same channel
        # sandbox uses, naming the projecting family — and nothing else. Still
        # far poorer than sandbox's six-plus provenance-ish fields.
        assert _hints(action) == {"source": "menu_fanout"}
        assert action.payload is None
        assert action.accepts is None
        assert _availability_exprs(action) == []
        assert _effect_exprs(action) == []
        assert action.trigger_phase is None
        assert action.return_phase is None
        # Real destination edge: the bound provider, not a self-loop.
        assert action.successor is not None
        assert action.successor is not hub


def test_menu_fanout_reprojection_and_provider_removal_cleanup() -> None:
    """Audit-table row: "Menu fanout" (cleanup owner: `_clear_dynamic_menu_actions`).

    Re-running PLANNING replaces the family's edges wholesale (fresh uids, no
    duplicates); a provider leaving the fanout requirement clears its action
    and only its action.
    """
    graph, hub = _enter_menu_hub()
    initial = _dynamic_actions(hub, "dynamic", "fanout", "menu")
    initial_ids = {action.uid for action in initial}

    _provision(hub, graph)
    refreshed = _dynamic_actions(hub, "dynamic", "fanout", "menu")

    assert len(refreshed) == len(initial) == 2
    assert {action.text for action in refreshed} == {"Listen to Aria", "Brew tea"}
    # Wholesale replacement is the current contract: stale uids are gone.
    assert initial_ids.isdisjoint({action.uid for action in refreshed})

    brew = next(node for node in graph.values() if getattr(node, "label", None) == "brew")
    brew.tags.discard("activity")
    _provision(hub, graph)
    remaining = _dynamic_actions(hub, "dynamic", "fanout", "menu")

    assert [action.text for action in remaining] == ["Listen to Aria"]


# ─────────────────────────────────────────────────────────────────────────────
# Row: Sandbox sponsored interactions (location / fixture / asset / mob)
# ─────────────────────────────────────────────────────────────────────────────


def test_sandbox_fixture_interaction_action_shape() -> None:
    """Audit-table row: "Sandbox sponsored interactions (location / fixture / asset / mob)".

    `_project_sandbox_interaction` is the shared sponsored-interaction stanza.
    Recorded differences from menu/game: machine label + display ``text``
    split, a per-interaction tag (``interaction:<label>``), and lifecycle
    provenance riding in ``ui_hints`` (a presentation channel).
    """
    compiled = SandboxSliceCompiler().compile(CHARACTERIZATION_SLICE)
    road = compiled.locations["road"]
    _provision(road, compiled.graph)

    pray = next(
        action
        for action in _dynamic_actions(road, "dynamic", "sandbox", "interaction")
        if action.ui_hints.model_dump().get("interaction") == "pray"
    )

    # Label pattern: sandbox_{source}_{location}_{sponsor}_{interaction}; the
    # source itself starts with "sandbox_", so the prefix doubles.
    assert pray.label == "sandbox_sandbox_fixture_road_altar_pray"
    assert pray.text == "Pray at the altar"
    assert pray.tags == {"dynamic", "sandbox", "interaction", "interaction:pray", "fixture"}
    # Sponsored-interaction provenance vocabulary, carried as ui_hints.
    assert _hints(pray) == {
        "source": "sandbox_fixture",
        "contribution": "interaction",
        "scope": "char_scope",
        "source_label": "altar",
        "source_kind": "fixture",
        "interaction": "pray",
        "target": "road",
        "return_to_location": False,
        "fixture": "altar",
    }
    assert pray.payload is None
    assert pray.accepts is None
    # Live availability rides on the edge as predicates (use-time), distinct
    # from the projection-time admission gates (sponsor in scope, visible,
    # target resolves, `once` not yet spent).
    assert _availability_exprs(pray) == ["True"]
    assert _effect_exprs(pray) == ["prayed = True"]
    assert pray.journal_text == "A hush settles over the road."
    assert pray.trigger_phase is None
    assert pray.return_phase is None
    assert pray.successor is road  # target "current" projects a self-loop


def test_sandbox_mob_interaction_call_and_return_shape() -> None:
    """Audit-table row: "Sandbox sponsored interactions (location / fixture / asset / mob)".

    ``return_to_location`` lowers to ``return_phase=PLANNING`` — the only
    family in this module that projects call semantics onto the edge.
    """
    compiled = SandboxSliceCompiler().compile(CHARACTERIZATION_SLICE)
    cave = compiled.locations["cave"]
    _provision(cave, compiled.graph)

    ask = next(
        action
        for action in _dynamic_actions(cave, "dynamic", "sandbox", "interaction")
        if action.ui_hints.model_dump().get("interaction") == "ask"
    )

    assert ask.label == "sandbox_sandbox_mob_cave_guide_ask"
    assert ask.tags == {"dynamic", "sandbox", "interaction", "interaction:ask", "mob"}
    assert _hints(ask) == {
        "source": "sandbox_mob",
        "contribution": "interaction",
        "scope": "char_scope",
        "source_label": "guide",
        "source_kind": "mob",
        "interaction": "ask",
        "target": "road",
        "return_to_location": True,
        "mob": "guide",
    }
    assert ask.successor is compiled.locations["road"]
    assert ask.trigger_phase is None
    assert ask.return_phase is ResolutionPhase.PLANNING


def test_sandbox_interaction_cleanup_is_scoped_to_owning_family() -> None:
    """Audit-table row: "Sandbox sponsored interactions (location / fixture / asset / mob)".

    Cleanup ownership is a compound key: source node ``edges_out`` x the
    ``{dynamic, sandbox, fixture}`` discriminator. Removing the sponsoring
    fixture and re-running only the fixture projector clears its actions and
    leaves every other family's edges untouched (same uids).
    """
    compiled = SandboxSliceCompiler().compile(CHARACTERIZATION_SLICE)
    road = compiled.locations["road"]
    graph = compiled.graph
    _provision(road, graph)

    # Re-projection is idempotent per family: same per-family counts.
    counts_before = {
        kind: len(_dynamic_actions(road, "dynamic", "sandbox", kind))
        for kind in ("movement", "wait", "event", "fixture")
    }
    _provision(road, graph)
    counts_after = {
        kind: len(_dynamic_actions(road, "dynamic", "sandbox", kind))
        for kind in ("movement", "wait", "event", "fixture")
    }
    assert counts_before == counts_after
    assert counts_after["fixture"] == 1  # pray
    assert counts_after["movement"] == 1  # east to cave

    other_family_ids = {
        action.uid
        for kind in ("movement", "wait", "event")
        for action in _dynamic_actions(road, "dynamic", "sandbox", kind)
    }

    road.fixtures.clear()
    project_sandbox_fixture_actions(
        caller=road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid)
    )

    assert _dynamic_actions(road, "dynamic", "sandbox", "fixture") == []
    surviving_ids = {
        action.uid
        for kind in ("movement", "wait", "event")
        for action in _dynamic_actions(road, "dynamic", "sandbox", kind)
    }
    assert surviving_ids == other_family_ids


# ─────────────────────────────────────────────────────────────────────────────
# Row: Sandbox scheduled events
# ─────────────────────────────────────────────────────────────────────────────


def test_sandbox_scheduled_event_action_shape() -> None:
    """Audit-table row: "Sandbox scheduled events".

    A matching scheduled event projects through the same
    `_project_sandbox_interaction` stanza (``event.as_interaction()``), with
    contribution kind ``event`` and the sponsoring scope as source.
    """
    compiled = SandboxSliceCompiler().compile(CHARACTERIZATION_SLICE)
    road = compiled.locations["road"]
    _provision(road, compiled.graph)

    dawn = next(
        iter(_dynamic_actions(road, "dynamic", "sandbox", "event")),
        None,
    )

    assert dawn is not None
    assert dawn.label == "sandbox_sandbox_schedule_road_char_scope_dawn"
    assert dawn.text == "Notice the dawn"
    assert dawn.tags == {"dynamic", "sandbox", "interaction", "interaction:dawn", "event"}
    assert _hints(dawn) == {
        "source": "sandbox_schedule",
        "contribution": "event",
        "scope": "char_scope",
        "source_label": "char_scope",
        "source_kind": "scope",
        "interaction": "dawn",
        "target": "road",
        "return_to_location": False,
        "event": "dawn",
    }
    assert dawn.payload is None
    assert dawn.accepts is None
    # The schedule gate is the projection-time admission predicate; nothing
    # lands on the edge as live availability ("Availability is after binding").
    assert _availability_exprs(dawn) == []
    assert dawn.trigger_phase is None
    assert dawn.return_phase is None
    assert dawn.successor is road


def test_sandbox_scheduled_event_admission_is_projection_time() -> None:
    """Audit-table row: "Sandbox scheduled events".

    ``event.matches(...)`` decides whether the edge is emitted at all — the
    gate is admission/binding, not an availability predicate on a persistent
    edge. A non-matching pass clears the family and projects nothing.
    """
    compiled = SandboxSliceCompiler().compile(CHARACTERIZATION_SLICE)
    road = compiled.locations["road"]
    graph = compiled.graph

    _provision(road, graph)  # world_turn 0 → period 1 → dawn matches
    assert len(_dynamic_actions(road, "dynamic", "sandbox", "event")) == 1

    road.locals["world_turn"] = 1  # period 2 → dawn (period=1) no longer matches
    _provision(road, graph)
    assert _dynamic_actions(road, "dynamic", "sandbox", "event") == []

    road.locals["world_turn"] = 0
    _provision(road, graph)
    assert len(_dynamic_actions(road, "dynamic", "sandbox", "event")) == 1


def test_sandbox_scheduled_event_cleanup_is_scoped_to_owning_family() -> None:
    """Audit-table row: "Sandbox scheduled events" (cleanup owner:
    `_clear_dynamic_sandbox_actions(action_kind="event")`).
    """
    compiled = SandboxSliceCompiler().compile(CHARACTERIZATION_SLICE)
    road = compiled.locations["road"]
    graph = compiled.graph
    _provision(road, graph)

    other_family_ids = {
        action.uid
        for kind in ("movement", "wait", "fixture")
        for action in _dynamic_actions(road, "dynamic", "sandbox", kind)
    }
    assert len(_dynamic_actions(road, "dynamic", "sandbox", "event")) == 1

    compiled.scope.scheduled_events.clear()
    project_sandbox_scheduled_events(
        caller=road, ctx=PhaseCtx(graph=graph, cursor_id=road.uid)
    )

    assert _dynamic_actions(road, "dynamic", "sandbox", "event") == []
    surviving_ids = {
        action.uid
        for kind in ("movement", "wait", "fixture")
        for action in _dynamic_actions(road, "dynamic", "sandbox", kind)
    }
    assert surviving_ids == other_family_ids


# ─────────────────────────────────────────────────────────────────────────────
# Row: Game self-loop moves
# ─────────────────────────────────────────────────────────────────────────────


def _rps_block() -> tuple[Graph, _RpsBlock]:
    graph = Graph(label="rps_characterization")
    block = _RpsBlock(label="rps_arena")
    graph.add(block)
    block.game_handler.setup(block.game)
    return graph, block


def test_game_self_loop_move_action_shape() -> None:
    """Audit-table row: "Game self-loop moves".

    Recorded, not fixed: these actions wear the ``fanout`` tag without ever
    touching ``Resolver.resolve_fanout`` — the tag vocabulary lies (see the
    audit table's drift column). Also recorded: the display text lives in
    ``label`` (``text`` stays empty), inverting the sandbox families' machine
    label + display ``text`` split. Since synthesis item D the only ``ui_hints``
    is the single ``source`` lifecycle token (``game_self_loop``, deliberately
    not ``game_fanout`` so it does not echo the fanout-tag lie).
    """
    graph, block = _rps_block()

    actions = provision_game_moves(block, ctx=PhaseCtx(graph=graph, cursor_id=block.uid))

    assert sorted(action.label for action in actions) == [
        "Play paper",
        "Play rock",
        "Play scissors",
    ]
    for action in actions:
        assert action.text == ""
        assert action.tags == {"dynamic", "fanout", "game"}
        assert _hints(action) == {"source": "game_self_loop"}
        assert action.accepts is None  # RPS declares no client input contract
        assert _availability_exprs(action) == []
        assert _effect_exprs(action) == []
        assert action.trigger_phase is None
        assert action.return_phase is None
        assert action.successor is block  # self-loop; the work happens in UPDATE

    rock = next(action for action in actions if action.label == "Play rock")
    assert rock.payload == {"move": RpsMove.ROCK}


def test_game_self_loop_reprojection_and_terminal_cleanup() -> None:
    """Audit-table row: "Game self-loop moves" (cleanup owner:
    `_clear_dynamic_game_actions`, ``{dynamic, fanout, game}`` on the cursor).

    Re-projection replaces the move set wholesale; a non-READY game clears the
    family and projects nothing.
    """
    graph, block = _rps_block()
    initial = provision_game_moves(block, ctx=PhaseCtx(graph=graph, cursor_id=block.uid))
    initial_ids = {action.uid for action in initial}

    refreshed = provision_game_moves(
        block, ctx=PhaseCtx(graph=graph, cursor_id=block.uid)
    )

    assert len(refreshed) == len(initial) == 3
    assert initial_ids.isdisjoint({action.uid for action in refreshed})
    assert len(_dynamic_actions(block, "dynamic", "fanout", "game")) == 3

    block.game.phase = GamePhase.TERMINAL
    result = provision_game_moves(block, ctx=PhaseCtx(graph=graph, cursor_id=block.uid))

    assert result == []
    assert _dynamic_actions(block, "dynamic", "fanout", "game") == []


# ─────────────────────────────────────────────────────────────────────────────
# Row: Incremental / cycle moves
# ─────────────────────────────────────────────────────────────────────────────


def _colony_sandbox() -> tuple[Graph, SandboxLocation, _ColonyBlock]:
    graph = Graph(label="colony_characterization")
    scope = SandboxScope(label="colony_scope", locals={"world_turn": 0})
    hub = SandboxLocation(label="colony_hub", location_name="Colony")
    colony = _ColonyBlock(label="colony_shell", content="The colony waits.")
    graph.add(scope)
    graph.add(hub)
    graph.add(colony)
    scope.add_child(hub)
    scope.add_child(colony)
    return graph, hub, colony


def test_incremental_move_action_shape() -> None:
    """Audit-table row: "Incremental / cycle moves".

    The fourth engine-side family: its own ``{dynamic, sandbox, incremental}``
    discriminator and clear helper, and hand-built hints that bypass
    `_sandbox_contribution_hints` — so, recorded difference, there is NO
    ``scope`` field even though the host is discovered via the scope. A
    convergence PR that folds these hints into the shared helper must update
    this test consciously.
    """
    assert sandbox_incremental.project_sandbox_incremental_game_moves is not None
    graph, hub, colony = _colony_sandbox()
    _provision(hub, graph)

    actions = _dynamic_actions(hub, "dynamic", "sandbox", "incremental")
    assert {action.text for action in actions} == {
        "Assign 1 worker to forage",
        "End cycle",
    }

    assign = next(a for a in actions if a.text == "Assign 1 worker to forage")
    assert assign.label == "sandbox_incremental_colony_shell_assign_forage"
    assert assign.tags == {"dynamic", "sandbox", "incremental"}
    hints = _hints(assign)
    assert hints == {
        "source": "sandbox_incremental_game",
        "contribution": "resource_allocation",
        "source_label": "colony_shell",
        "source_kind": "game",
        "move": "assign",
        "target": "forage",
    }
    # The recorded gap: near-duplicate of the sandbox hint vocabulary, minus
    # the scope field the shared helper would have added.
    assert "scope" not in hints
    assert assign.accepts is None
    assert _availability_exprs(assign) == []
    assert assign.trigger_phase is None
    assert assign.return_phase is None
    assert assign.successor is hub  # self-loop hosted through the location
    # Payload carries the host uid, the typed move, and a typed time cost —
    # zero-duration allocation vs end-cycle time cost.
    assert set(assign.payload) == {"sandbox_incremental_game", "move", "sandbox_time_cost"}
    assert assign.payload["sandbox_incremental_game"] == colony.uid
    assert assign.payload["move"].kind == "assign"
    assert isinstance(assign.payload["sandbox_time_cost"], SandboxTimeCost)
    assert assign.payload["sandbox_time_cost"].kind == "resource_allocation"
    assert assign.payload["sandbox_time_cost"].duration == 0

    end_cycle = next(a for a in actions if a.text == "End cycle")
    assert end_cycle.label == "sandbox_incremental_colony_shell_end_cycle_cycle"
    assert end_cycle.payload["sandbox_time_cost"].kind == "resource_cycle"
    assert end_cycle.payload["sandbox_time_cost"].duration == 1


def test_incremental_cleanup_is_scoped_to_owning_family() -> None:
    """Audit-table row: "Incremental / cycle moves" (cleanup owner:
    `_clear_incremental_actions`, the family's own helper).

    Re-projection is idempotent; a terminal/non-READY host clears the family
    and leaves the other sandbox families' edges untouched (same uids).
    """
    graph, hub, colony = _colony_sandbox()
    _provision(hub, graph)

    assert len(_dynamic_actions(hub, "dynamic", "sandbox", "incremental")) == 2
    _provision(hub, graph)
    assert len(_dynamic_actions(hub, "dynamic", "sandbox", "incremental")) == 2

    other_family_ids = {
        action.uid for action in _dynamic_actions(hub, "dynamic", "sandbox", "wait")
    }
    assert other_family_ids

    colony.game.phase = GamePhase.TERMINAL
    sandbox_incremental.project_sandbox_incremental_game_moves(
        caller=hub, ctx=PhaseCtx(graph=graph, cursor_id=hub.uid)
    )

    assert _dynamic_actions(hub, "dynamic", "sandbox", "incremental") == []
    assert {
        action.uid for action in _dynamic_actions(hub, "dynamic", "sandbox", "wait")
    } == other_family_ids


# ─────────────────────────────────────────────────────────────────────────────
# Rows: Adventure movement hazards (world-owned overlay)
# ─────────────────────────────────────────────────────────────────────────────


def _repo_worlds_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "worlds"


def _adventure_ledger() -> Ledger:
    bundle = WorldBundle.load(_repo_worlds_dir() / "adventure_sandbox_slice")
    world = WorldCompiler().compile(bundle)
    result = world.create_story("adventure_sandbox_slice", init_mode=InitMode.EAGER)
    ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
    enter = next(
        edge
        for edge in ledger.cursor.edges_out()
        if isinstance(edge, Action) and edge.text == "Stand at the end of the road"
    )
    ledger.resolve_choice(enter.uid)
    return ledger


def _provision_sandbox_actions(ledger: Ledger) -> list[Action]:
    assert isinstance(ledger.cursor, SandboxLocation)
    do_provision(
        ledger.cursor,
        ctx=PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor.uid),
    )
    return [
        edge
        for edge in ledger.cursor.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox"}.issubset(edge.tags)
    ]


def _choose(ledger: Ledger, **hints: str) -> Action:
    for action in _provision_sandbox_actions(ledger):
        action_hints = action.ui_hints.model_dump()
        if all(action_hints.get(key) == value for key, value in hints.items()):
            ledger.resolve_choice(action.uid, choice_payload=action.payload)
            return action
    raise AssertionError(f"No sandbox action at {ledger.cursor.label!r} matched {hints!r}")


def _walk_to_hall_of_mists_with_nugget() -> Ledger:
    ledger = _adventure_ledger()
    _choose(ledger, contribution="movement", direction="east")
    _choose(ledger, contribution="take", asset="keys")
    _choose(ledger, contribution="take", asset="brass_lamp")
    _choose(ledger, contribution="light", asset="brass_lamp", verb="turn_on")
    _choose(ledger, contribution="movement", direction="west")
    _choose(ledger, contribution="movement", direction="south")
    _choose(ledger, contribution="movement", direction="south")
    _choose(ledger, contribution="movement", direction="south")
    _choose(ledger, contribution="unlock", target="grate")
    _choose(ledger, contribution="open", target="grate")
    _choose(ledger, contribution="movement", direction="down")
    _choose(ledger, contribution="movement", direction="west")
    _choose(ledger, contribution="take", asset="gold_nugget")
    _choose(ledger, contribution="movement", direction="west")
    assert ledger.cursor.label == "hall_of_mists"
    return ledger


def _movement_actions(location, direction: str) -> list[Action]:
    return [
        action
        for action in location.edges_out(Selector(has_kind=Action))
        if {"dynamic", "sandbox", "movement"}.issubset(action.tags or set())
        and (action.ui_hints.model_dump().get("direction") if action.ui_hints else None)
        == direction
    ]


def test_adventure_hazard_overlay_action_shape() -> None:
    """Audit-table row: "Adventure movement hazards".

    A world-owned overlay: the projected movement action is deleted and
    rewritten as a self-loop that still presents as attempted movement (a
    protected projection difference). Recorded: its tag set
    ``{dynamic, sandbox, adventure, movement, hazard}`` is a superset of BOTH
    the world's ``{dynamic, sandbox, adventure}`` discriminator and the
    engine's ``{dynamic, sandbox, movement}`` discriminator — the one live
    counter-example to exactly-one-family cleanup ownership (and why the
    adventure family is excluded from FAMILY_DISCRIMINATORS in
    test_sandbox_architecture.py). The hints are the inherited movement hints
    with world-authority fields overwritten on top — including a ``target``
    that still names the original destination the self-loop never reaches.
    """
    ledger = _walk_to_hall_of_mists_with_nugget()
    hall = ledger.cursor
    do_provision(hall, ctx=PhaseCtx(graph=ledger.graph, cursor_id=hall.uid))

    hazards = [a for a in _movement_actions(hall, "up") if "hazard" in a.tags]
    assert len(hazards) == 1
    hazard = hazards[0]

    assert hazard.label == "adventure_hazard_hall_of_mists_up"
    assert hazard.tags == {"dynamic", "sandbox", "adventure", "movement", "hazard"}
    assert hazard.text == "Go up to At Top of Small Pit"  # presents as attempted movement
    assert hazard.successor is hall  # but self-loops: the move is denied
    hints = _hints(hazard)
    assert hints == {
        # Inherited from the engine movement action it rewrote:
        "source": "sandbox_link",
        "scope": "cave",
        "source_label": "hall_of_mists",
        "direction": "up",
        "raw_direction": "up",
        "target": "top_of_small_pit",
        # Overwritten by the world overlay:
        "source_kind": "world_authority",
        "contribution": "movement_hazard",
        "hazard_outcome": "block",
    }
    # Recorded difference: the world builds its time cost as a plain dict,
    # not a SandboxTimeCost instance like the engine families.
    assert hazard.payload == {
        "adventure_action": "movement_hazard",
        "sandbox_time_cost": {"kind": "adventure", "duration": 0},
        "direction": "up",
        "outcome": "block",
    }
    assert hazard.journal_text == (
        "I'm not sure you'll be able to get up it with what you're carrying."
    )
    assert hazard.accepts is None
    assert _availability_exprs(hazard) == []  # the hazard fires on selection


def test_adventure_hazard_rewrite_survives_repeated_planning_passes() -> None:
    """Audit-table row: "Adventure movement hazards" — pins the rewrite ordering.

    The hazard action wears the engine's ``{dynamic, sandbox, movement}``
    discriminator, so `_clear_dynamic_sandbox_actions(action_kind="movement")`
    deletes it on EVERY planning pass; `project_adventure_world_actions`
    (Priority.LAST) then re-rewrites the regenerated movement action. That
    projector re-run priority ordering is load-bearing: this test fails if the
    world projector stops running after the engine movement projector. Per
    pass: hazards survive, exactly one hazard per hazarded direction, and no
    plain movement action leaks through for that direction.
    """
    ledger = _walk_to_hall_of_mists_with_nugget()
    hall = ledger.cursor

    for _ in range(3):
        do_provision(hall, ctx=PhaseCtx(graph=ledger.graph, cursor_id=hall.uid))

        up_actions = _movement_actions(hall, "up")
        hazards = [a for a in up_actions if "hazard" in a.tags]
        plain_up = [a for a in up_actions if "adventure" not in a.tags]
        assert len(hazards) == 1
        assert plain_up == []

        # Non-hazarded directions stay plain engine movement.
        east = _movement_actions(hall, "east")
        assert len(east) == 1
        assert "hazard" not in east[0].tags
        assert east[0].tags == {"dynamic", "sandbox", "movement"}

    # Removing the admission condition (drop the nugget) restores plain
    # movement and clears the hazard — the overlay's stale edge does not linger.
    _choose(ledger, contribution="drop", asset="gold_nugget")
    do_provision(hall, ctx=PhaseCtx(graph=ledger.graph, cursor_id=hall.uid))

    up_actions = _movement_actions(hall, "up")
    assert [a.tags for a in up_actions] == [{"dynamic", "sandbox", "movement"}]
