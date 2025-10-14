"""Tests for :mod:`tangl.story.reference_domain.block`."""

from __future__ import annotations

from tangl.core import BaseFragment, Graph
from tangl.story.episode import SimpleBlock, SimpleConcept
from tangl.vm import ChoiceEdge, Frame, ResolutionPhase as P


def _by_fragment_type(fragments: list[BaseFragment], fragment_type: str) -> list[BaseFragment]:
    return [f for f in fragments if isinstance(f, BaseFragment) and f.fragment_type == fragment_type]


def test_block_stores_inline_content() -> None:
    block = SimpleBlock(label="block", content="Inline text")

    assert block.content == "Inline text"
    assert block.label == "block"


def test_get_concepts_returns_only_concepts() -> None:
    g = Graph(label="test")
    block = SimpleBlock(graph=g, label="parent")
    concept = SimpleConcept(graph=g, label="child", content="text")
    other = SimpleBlock(graph=g, label="other")

    g.add_edge(block, concept)
    g.add_edge(block, other)

    concepts = block.get_concepts()

    assert concepts == [concept]


def test_get_choices_filters_by_availability() -> None:
    g = Graph(label="test")
    start = SimpleBlock(graph=g, label="start")
    left = SimpleBlock(graph=g, label="left")
    right = SimpleBlock(graph=g, label="right")

    locked = ChoiceEdge(graph=g, source_id=start.uid, destination_id=left.uid, label="locked")
    open_edge = ChoiceEdge(graph=g, source_id=start.uid, destination_id=right.uid, label="open")

    locked.predicate = lambda ns: ns.get("has_key", False)

    assert start.get_choices() == [locked, open_edge]
    assert start.get_choices(ns={"has_key": False}) == [open_edge]
    assert start.get_choices(ns={"has_key": True}) == [locked, open_edge]


def test_block_journal_renders_inline_content() -> None:
    g = Graph(label="test")
    block = SimpleBlock(graph=g, label="block", content="Inline text")

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    inline = _by_fragment_type(fragments, "block_content")
    assert len(inline) == 1
    assert "Inline text" in inline[0].content


def test_block_journal_renders_child_concepts() -> None:
    g = Graph(label="test")
    block = SimpleBlock(graph=g, label="block")
    first = SimpleConcept(graph=g, label="first", content="First")
    second = SimpleConcept(graph=g, label="second", content="Second")
    g.add_edge(block, first)
    g.add_edge(block, second)

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    concept_frags = _by_fragment_type(fragments, "concept")
    assert len(concept_frags) == 2
    contents = {f.content for f in concept_frags}
    assert {"First", "Second"} <= contents


def test_block_journal_renders_choice_menu() -> None:
    g = Graph(label="test")
    start = SimpleBlock(graph=g, label="start")
    left = SimpleBlock(graph=g, label="left")
    right = SimpleBlock(graph=g, label="right")
    ChoiceEdge(graph=g, source_id=start.uid, destination_id=left.uid, label="Left")
    ChoiceEdge(graph=g, source_id=start.uid, destination_id=right.uid, label="Right")

    frame = Frame(graph=g, cursor_id=start.uid)
    fragments = frame.run_phase(P.JOURNAL)

    menus = _by_fragment_type(fragments, "choice_menu")
    assert len(menus) == 1
    menu_text = menus[0].content
    assert "1. Left" in menu_text
    assert "2. Right" in menu_text


def test_block_with_concepts_and_choices_emits_all_fragments() -> None:
    g = Graph(label="test")
    block = SimpleBlock(graph=g, label="tavern", content="You enter the tavern.")
    smell = SimpleConcept(graph=g, label="smell", content="It smells of ale.")
    sound = SimpleConcept(graph=g, label="sound", content="Music plays softly.")
    g.add_edge(block, smell)
    g.add_edge(block, sound)

    bar = SimpleBlock(graph=g, label="bar")
    corner = SimpleBlock(graph=g, label="corner")
    ChoiceEdge(graph=g, source_id=block.uid, destination_id=bar.uid, label="Approach bar")
    ChoiceEdge(graph=g, source_id=block.uid, destination_id=corner.uid, label="Find corner")

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    inline = _by_fragment_type(fragments, "block_content")
    concepts = _by_fragment_type(fragments, "concept")
    menus = _by_fragment_type(fragments, "choice_menu")

    assert inline and concepts and menus

    inline_index = fragments.index(inline[0])
    first_concept_index = fragments.index(concepts[0])
    menu_index = fragments.index(menus[0])

    assert inline_index < first_concept_index < menu_index
