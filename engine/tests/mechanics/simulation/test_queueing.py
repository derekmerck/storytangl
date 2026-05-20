"""Tests for deterministic simulation and queueing mechanics."""

from __future__ import annotations

import pytest
from pydantic import Field

from tangl.core import Graph
from tangl.core.bases import BaseModelPlus
from tangl.journal.fragments import ContentFragment
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.handlers import provision_game_moves
from tangl.mechanics.sandbox.time import advance_world_turn_to
from tangl.mechanics.simulation import (
    EventCalendar,
    QueueMove,
    QueueSimulation,
    QueueSimulationHandler,
    QueueStationSpec,
    SimulationEvent,
)
from tangl.story import Action, Block
from tangl.vm import Frame, Ledger, TraversableEdge as ChoiceEdge


class ClockSource(BaseModelPlus):
    """Minimal locals-bearing object for clock helper tests."""

    locals: dict[str, object] = Field(default_factory=dict)


class QueueBlock(HasGame, Block):
    """Test block embedding the queue simulation."""

    _game_class = QueueSimulation
    _game_handler_class = QueueSimulationHandler


def _ed_game(*, projection_mode: str = "log") -> QueueSimulation:
    return QueueSimulation(
        patient_arrivals={
            "P1": 0,
            "P2": 2,
            "P3": 4,
            "P4": 8,
        },
        station_specs={
            "triage": QueueStationSpec(
                capacity=1,
                service_turns=3,
                next_station="imaging",
            ),
            "imaging": QueueStationSpec(
                capacity=1,
                service_turns=5,
                next_station="disposition",
            ),
            "disposition": QueueStationSpec(
                capacity=1,
                service_turns=2,
                next_station=None,
            ),
        },
        entry_station="triage",
        projection_mode=projection_mode,
    )


def _run_to_completion(game: QueueSimulation) -> QueueSimulationHandler:
    handler = QueueSimulationHandler()
    handler.setup(game)
    handler.receive_move(game, QueueMove("run_until_complete"))
    return handler


def test_advance_world_turn_to_advances_and_rejects_backwards() -> None:
    source = ClockSource(locals={"world_turn": 2})

    assert advance_world_turn_to(source, 5) == 3
    assert source.locals["world_turn"] == 5
    assert advance_world_turn_to(source, 5) == 0

    with pytest.raises(ValueError, match="target_turn"):
        advance_world_turn_to(source, 4)


def test_event_calendar_peeks_and_pops_by_turn_then_sequence() -> None:
    calendar = EventCalendar()
    later = calendar.push(SimulationEvent(label="later", at_turn=3, kind="x"))
    first = calendar.push(SimulationEvent(label="first", at_turn=1, kind="x"))
    second = calendar.push(SimulationEvent(label="second", at_turn=1, kind="x"))

    assert calendar.peek_next() is first
    assert len(calendar) == 3
    assert calendar.pop_next() is first
    assert calendar.pop_next() is second
    assert calendar.pop_next() is later
    assert calendar.pop_next() is None


def test_queueing_run_processes_events_in_order_and_completes_patients() -> None:
    game = _ed_game()
    _run_to_completion(game)

    assert [event.turn for event in game.trace] == sorted(event.turn for event in game.trace)
    assert game.completed == ["P1", "P2", "P3", "P4"]
    assert game.metrics is not None
    assert game.metrics.completed_count == 4
    assert game.metrics.completed_turn == 25
    assert game.metrics.mean_length_of_stay == 14.0
    assert game.metrics.mean_wait == 4.0
    assert game.metrics.bottleneck == "imaging"
    assert game.metrics.utilization == {
        "triage": 0.48,
        "imaging": 0.8,
        "disposition": 0.32,
    }


def test_queueing_empty_run_can_complete() -> None:
    game = QueueSimulation(
        station_specs={"triage": QueueStationSpec()},
        entry_station="triage",
    )
    handler = QueueSimulationHandler()
    handler.setup(game)

    assert [move.kind for move in handler.get_available_moves(game)] == ["run_until_complete"]

    handler.receive_move(game, QueueMove("run_until_complete"))

    assert game.metrics is not None
    assert game.metrics.completed_count == 0
    assert game.metrics.completed_turn == 0


def test_queueing_rejects_non_terminating_topology() -> None:
    game = QueueSimulation(
        patient_arrivals={"P1": 0},
        station_specs={
            "triage": QueueStationSpec(next_station="imaging"),
            "imaging": QueueStationSpec(next_station="triage"),
        },
        entry_station="triage",
    )

    with pytest.raises(ValueError, match="cycle"):
        QueueSimulationHandler().setup(game)


def test_queueing_capacity_and_fifo_order_are_respected() -> None:
    game = _ed_game()
    _run_to_completion(game)

    for station_label, station in game.stations.items():
        boundaries: list[tuple[int, int]] = []
        for patient in game.patients.values():
            if station_label not in patient.service_start:
                continue
            boundaries.append((patient.service_start[station_label], 1))
            boundaries.append((patient.service_end[station_label], -1))
        active = 0
        for _, delta in sorted(boundaries):
            active += delta
            assert active <= station.capacity

    assert [
        patient.label
        for patient in sorted(
            game.patients.values(),
            key=lambda patient: patient.service_start["triage"],
        )
    ] == ["P1", "P2", "P3", "P4"]


def test_queueing_log_and_narrative_projection_share_trace() -> None:
    log_game = _ed_game(projection_mode="log")
    narrative_game = _ed_game(projection_mode="narrative")
    log_handler = _run_to_completion(log_game)
    narrative_handler = _run_to_completion(narrative_game)

    assert [event.model_dump() for event in log_game.latest_trace] == [
        event.model_dump() for event in narrative_game.latest_trace
    ]
    log_fragments = log_handler.get_journal_fragments(log_game)
    narrative_fragments = narrative_handler.get_journal_fragments(narrative_game)
    assert log_fragments is not None
    assert narrative_fragments is not None
    assert isinstance(log_fragments[0], ContentFragment)
    assert "—" in log_fragments[0].content
    assert "the doors open" in narrative_fragments[0].content


def test_queueing_hasgame_provisions_self_loop_and_journals_fragments() -> None:
    graph = Graph(label="queueing_flow")
    intro = graph.add_node(kind=Block, label="intro")
    block = graph.add_node(kind=QueueBlock, label="queue")
    block._game = _ed_game()
    ChoiceEdge(
        graph=graph,
        predecessor_id=intro.uid,
        successor_id=block.uid,
        label="Run queue",
    )

    ledger = Ledger.from_graph(graph=graph, entry_id=intro.uid)
    enter = next(edge for edge in ledger.cursor.edges_out() if edge.label == "Run queue")
    ledger.resolve_choice(enter.uid)

    frame = Frame(graph=graph, cursor=ledger.cursor)
    ctx = frame._make_ctx()
    object.__setattr__(ctx, "_frame", frame)
    actions = provision_game_moves(ledger.cursor, ctx=ctx)
    labels = {action.label for action in actions}
    assert labels == {"Run next event", "Run until complete"}

    run_next = next(
        action
        for action in ledger.cursor.edges_out()
        if isinstance(action, Action) and action.label == "Run next event"
    )
    ledger.resolve_choice(run_next.uid, choice_payload=run_next.payload)

    assert ledger.cursor_id == block.uid
    content = [
        fragment.content
        for fragment in ledger.get_journal()
        if isinstance(fragment, ContentFragment)
    ]
    assert any("P1 arrives and enters triage" in item for item in content)
    assert any("P1 starts triage" in item for item in content)
