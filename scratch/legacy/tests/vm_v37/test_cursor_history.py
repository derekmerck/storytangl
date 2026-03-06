"""Tests for cursor history tracking."""
from uuid import uuid4

from tangl.core import Graph, StreamRegistry
from tangl.vm import ChoiceEdge, Frame, Ledger


def test_ledger_cursor_history_starts_empty():
    """New ledgers start with an empty history list."""

    graph = Graph(label="test")
    start = graph.add_node(label="start")

    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())

    assert ledger.cursor_history == []
    assert isinstance(ledger.cursor_history, list)


def test_history_appends_on_follow():
    """History records each destination after ``follow_edge``."""

    graph = Graph(label="test")
    node_a = graph.add_node(label="A")
    node_b = graph.add_node(label="B")
    node_c = graph.add_node(label="C")

    edge_ab = ChoiceEdge(graph=graph, source_id=node_a.uid, destination_id=node_b.uid)
    edge_bc = ChoiceEdge(graph=graph, source_id=node_b.uid, destination_id=node_c.uid)

    frame = Frame(graph=graph, cursor_id=node_a.uid, cursor_history=[], step=0)

    frame.follow_edge(edge_ab)
    assert frame.cursor_history == [node_b.uid]
    assert frame.cursor_id == node_b.uid

    frame.follow_edge(edge_bc)
    assert frame.cursor_history == [node_b.uid, node_c.uid]
    assert frame.cursor_id == node_c.uid


def test_history_includes_self_loops():
    """Self-loops are logged as consecutive duplicates."""

    graph = Graph(label="test")
    game = graph.add_node(label="game")
    loop_edge = ChoiceEdge(graph=graph, source_id=game.uid, destination_id=game.uid)

    frame = Frame(graph=graph, cursor_id=game.uid, cursor_history=[], step=0)

    for _ in range(3):
        frame.follow_edge(loop_edge)

    assert frame.cursor_history == [game.uid, game.uid, game.uid]
    assert frame.cursor_id == game.uid
    assert frame.step == 3


def test_ledger_and_frame_share_history():
    """Frame history mutations are visible on the ledger."""

    graph = Graph(label="test")
    node_a = graph.add_node(label="A")
    node_b = graph.add_node(label="B")
    edge_ab = ChoiceEdge(graph=graph, source_id=node_a.uid, destination_id=node_b.uid)

    ledger = Ledger(graph=graph, cursor_id=node_a.uid, records=StreamRegistry())
    frame = ledger.get_frame()

    assert frame.cursor_history is ledger.cursor_history

    frame.follow_edge(edge_ab)

    assert ledger.cursor_history == [node_b.uid]


def test_turn_starts_at_zero():
    """Turn is zero when no positions have been recorded."""

    graph = Graph(label="test")
    node_a = graph.add_node(label="A")

    ledger = Ledger(graph=graph, cursor_id=node_a.uid, records=StreamRegistry())

    assert ledger.turn == 0


def test_turn_increments_on_position_change():
    """Turn increments whenever the position changes to a new node."""

    graph = Graph(label="test")
    node_a = graph.add_node(label="A")
    node_b = graph.add_node(label="B")
    node_c = graph.add_node(label="C")

    ledger = Ledger(graph=graph, cursor_id=node_a.uid, records=StreamRegistry())
    ledger.cursor_history = [node_a.uid, node_b.uid, node_c.uid]

    assert ledger.turn == 3


def test_turn_does_not_increment_on_self_loop():
    """Turn ignores consecutive duplicate positions."""

    graph = Graph(label="test")
    node = graph.add_node(label="loop")

    ledger = Ledger(graph=graph, cursor_id=node.uid, records=StreamRegistry())
    ledger.cursor_history = [node.uid, node.uid, node.uid]

    assert ledger.turn == 1


def test_turn_mixed_moves_and_loops():
    """Turn counts only unique moves within mixed histories."""

    graph = Graph(label="test")
    node_a = graph.add_node(label="A")
    node_b = graph.add_node(label="B")

    ledger = Ledger(graph=graph, cursor_id=node_a.uid, records=StreamRegistry())
    ledger.cursor_history = [node_a.uid, node_b.uid, node_b.uid, node_b.uid, node_a.uid]

    assert ledger.turn == 3


def test_compute_turn_static_method():
    """``_compute_turn`` mirrors the ``turn`` property."""

    node_a, node_b, node_c = uuid4(), uuid4(), uuid4()

    assert Ledger._compute_turn([]) == 0
    assert Ledger._compute_turn([node_a]) == 1
    assert Ledger._compute_turn([node_a, node_b, node_c]) == 3
    assert Ledger._compute_turn([node_a, node_a, node_a]) == 1
    assert Ledger._compute_turn([node_a, node_b, node_b, node_a, node_a]) == 3
