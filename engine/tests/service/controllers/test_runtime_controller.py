from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import Graph, StreamRegistry
from tangl.journal.content import ContentFragment
from tangl.service.controllers import RuntimeController
from tangl.vm.frame import ChoiceEdge, ResolutionPhase
from tangl.vm.ledger import Ledger


@pytest.fixture()
def runtime_controller() -> RuntimeController:
    return RuntimeController()


@pytest.fixture()
def ledger() -> Ledger:
    graph = Graph(label="demo")
    start = graph.add_node(label="start")
    return Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())


def test_get_journal_entries_limits_results(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    ledger.records.push_records(
        ContentFragment(content="first"),
        marker_type="journal",
        marker_name="entry-0001",
    )
    ledger.records.push_records(
        ContentFragment(content="second"),
        marker_type="journal",
        marker_name="entry-0002",
    )

    result = runtime_controller.get_journal_entries(ledger, limit=1)
    assert [fragment.content for fragment in result] == ["second"]


def test_resolve_choice_advances_cursor_and_collects_fragments(
    runtime_controller: RuntimeController,
    ledger: Ledger,
) -> None:
    graph = ledger.graph
    start = graph.get(ledger.cursor_id)
    end = graph.add_node(label="end")
    ChoiceEdge(graph=graph, source_id=start.uid, destination_id=end.uid, label="choice")
    frame = ledger.get_frame()

    @frame.local_domain.handlers.register(phase=ResolutionPhase.JOURNAL)
    def _journal_handler(*_, ctx, **__) -> list[ContentFragment]:
        return [ContentFragment(content=f"cursor:{ctx.cursor.label}")]

    frame._invalidate_context()

    result = runtime_controller.resolve_choice(frame, graph.find_edge(label="choice").uid)
    assert result["cursor_id"] == end.uid
    assert result["step"] == frame.step
    contents = [getattr(fragment, "content", None) for fragment in result["fragments"]]
    assert "cursor:end" in contents


def test_jump_to_node_runs_journal(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    graph = ledger.graph
    graph.add_node(label="branch")
    target = graph.find_node(label="branch")
    frame = ledger.get_frame()

    @frame.local_domain.handlers.register(phase=ResolutionPhase.JOURNAL)
    def _journal_handler(*_, ctx, **__) -> list[ContentFragment]:
        return [ContentFragment(content=f"cursor:{ctx.cursor.label}")]

    frame._invalidate_context()

    result = runtime_controller.jump_to_node(frame, target.uid)
    assert result["cursor_id"] == target.uid
    contents = [getattr(fragment, "content", None) for fragment in result["fragments"]]
    assert "cursor:branch" in contents


def test_get_story_info_reports_metadata(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    info = runtime_controller.get_story_info(ledger)
    assert info["cursor_id"] == ledger.cursor_id
    assert info["journal_size"] == 0
    assert info["title"] == ledger.graph.label


def test_get_available_choices_returns_metadata(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    graph = ledger.graph
    start = graph.get(ledger.cursor_id)
    end = graph.add_node(label="end")
    choice = ChoiceEdge(graph=graph, source_id=start.uid, destination_id=end.uid, label="go")

    result = runtime_controller.get_available_choices(ledger)
    assert result == [{"uid": choice.uid, "label": "go"}]


def test_get_journal_entries_rejects_negative_limit(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    with pytest.raises(ValueError):
        runtime_controller.get_journal_entries(ledger, limit=-1)


def test_resolve_choice_requires_choice(runtime_controller: RuntimeController, ledger: Ledger) -> None:
    frame = ledger.get_frame()
    bogus_choice_id = uuid4()
    with pytest.raises(ValueError, match="Choice"):
        runtime_controller.resolve_choice(frame, bogus_choice_id)
