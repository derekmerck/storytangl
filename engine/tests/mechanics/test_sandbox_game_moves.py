"""Hosted game authority and time payment through JSON-restored sandbox actions."""

from __future__ import annotations

import json
import random
from uuid import UUID, uuid4

import pytest

from tangl.core import Graph, Selector
from tangl.mechanics.games import (
    HasGame, IncrementalGame, IncrementalGameHandler, IncrementalMove, TaskSpec,
)
from tangl.mechanics.sandbox import SandboxLocation, SandboxScope
from tangl.mechanics.sandbox import incremental  # noqa: F401 -- registers the adapter
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, Block
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.dispatch import do_provision, do_validate
from tangl.vm.runtime.frame import PhaseCtx


class JsonHostedColony(IncrementalGame):
    starting_resources: dict[str, int] = {"food": 1}
    starting_workers: int = 1
    task_specs: dict[str, TaskSpec] = {"forage": TaskSpec(produces={"food": 2})}
    upkeep: dict[str, int] = {"food": 1}
    unlocked_tasks: list[str] = ["forage"]


class JsonHostedColonyBlock(HasGame, Block):
    _game_class = JsonHostedColony
    _game_handler_class = IncrementalGameHandler


def _reload(ledger: Ledger) -> Ledger:
    return Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))


def _colony_ledger() -> tuple[Ledger, UUID, UUID]:
    graph = Graph()
    scope = graph.add_node(kind=SandboxScope, label="scope", locals={"world_turn": 0})
    hub = graph.add_node(kind=SandboxLocation, label="hub")
    host = graph.add_node(kind=JsonHostedColonyBlock, label="colony")
    other = graph.add_node(kind=JsonHostedColonyBlock, label="other_colony")
    for child in (hub, host, other):
        scope.add_child(child)
    do_provision(hub, ctx=PhaseCtx(graph=graph, cursor_id=hub.uid))
    return _reload(Ledger.from_graph(graph, entry_id=hub.uid)), host.uid, other.uid


def _action(ledger: Ledger, host_id: UUID, kind: str) -> Action:
    return next(
        edge for edge in ledger.cursor.edges_out()
        if isinstance(edge, Action) and isinstance(edge.payload, dict)
        and edge.payload.get("sandbox_incremental_game") == host_id
        and edge.payload["move"]["kind"] == kind
    )


def _snapshot(ledger: Ledger):
    return Json.serialize(ledger.unstructure()), random.getstate()


def test_hosted_incremental_json_restore_preserves_allocation_and_tick_payment() -> None:
    ledger, host_id, _ = _colony_ledger()
    assign = _action(ledger, host_id, "assign")
    # Ordinary JSON wire decoding leaves the host id a string, not a UUID.
    echo = json.loads(Json.serialize(assign.payload))
    ctx = ledger.get_frame()._make_ctx(incoming_edge=assign, incoming_payload=echo)
    ctx.current_phase = ResolutionPhase.VALIDATE
    before = _snapshot(ledger)
    for _ in range(3):
        assert do_validate(assign, ctx=ctx)
    assert _snapshot(ledger) == before
    ledger.resolve_choice(assign.uid, choice_payload=echo)
    host = ledger.graph.get(host_id)
    assert host.game.task_assignments == {"forage": 1}
    assert host.game.history[-1].player_move == IncrementalMove("assign", "forage")
    assert ledger.graph.find_node(Selector(label="scope")).locals["world_turn"] == 0

    ledger = _reload(ledger)
    host = ledger.graph.get(host_id)
    assert isinstance(host.game_state.history[-1].player_move, IncrementalMove)
    cycle = _action(ledger, host_id, "end_cycle")
    ledger.resolve_choice(cycle.uid, choice_payload=json.loads(Json.serialize(cycle.payload)))
    assert ledger.graph.find_node(Selector(label="scope")).locals["world_turn"] == 1
    assert host.game.cycle == 1
    assert host.game.resources["food"] == 2


@pytest.mark.parametrize("attack", ["host", "missing_host", "cost", "move", "malformed", "extra"])
def test_hosted_rejections_leave_live_ledger_games_and_clock_unchanged(attack: str) -> None:
    ledger, host_id, other_id = _colony_ledger()
    edge = _action(ledger, host_id, "assign")
    payload = json.loads(Json.serialize(edge.payload))
    if attack == "host":
        payload["sandbox_incremental_game"] = str(other_id)
    elif attack == "missing_host":
        payload["sandbox_incremental_game"] = str(uuid4())
    elif attack == "cost":
        payload["sandbox_time_cost"]["duration"] = 8
    elif attack == "move":
        payload["move"] = {"kind": "end_cycle"}  # Well-formed and legal, but not offered here.
    elif attack == "malformed":
        payload["move"] = {"kind": "assign", "target": {"bad": "shape"}}
    else:
        payload["unlisted_input"] = True
    before = _snapshot(ledger)
    with pytest.raises(ValueError):
        ledger.resolve_choice(edge.uid, choice_payload=payload)
    assert _snapshot(ledger) == before
