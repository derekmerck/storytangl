from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import Graph, StreamRegistry
from tangl.vm.frame import ChoiceEdge, ResolutionPhase
from tangl.vm.ledger import Ledger


def test_init_cursor_generates_journal_entry() -> None:
    graph = Graph(label="test")
    start = graph.add_node(label="start")

    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    assert ledger.step == 0
    assert list(ledger.records.iter_channel("fragment")) == []

    ledger.init_cursor()

    assert ledger.step >= 1
    fragments = list(ledger.records.iter_channel("fragment"))
    assert fragments


def test_init_cursor_follows_prereq_redirects() -> None:
    graph = Graph(label="test")
    start = graph.add_node(label="start")
    forced = graph.add_node(label="forced_destination")

    ChoiceEdge(
        graph=graph,
        source_id=start.uid,
        destination_id=forced.uid,
        trigger_phase=ResolutionPhase.PREREQS,
    )

    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()

    ledger.init_cursor()

    assert ledger.cursor_id == forced.uid
    assert ledger.step >= 1


def test_init_cursor_with_invalid_cursor_raises() -> None:
    graph = Graph(label="test")
    ledger = Ledger(graph=graph, cursor_id=uuid4(), records=StreamRegistry())

    with pytest.raises(RuntimeError, match="not found in graph"):
        ledger.init_cursor()
