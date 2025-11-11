"""Tests for :mod:`tangl.story.reference_domain.block`."""

from __future__ import annotations

from tangl.core import BaseFragment
from tangl.story.episode import Block, Action
from tangl.story.concepts import Concept
from tangl.story.story_graph import StoryGraph
from tangl.vm import ChoiceEdge, Frame, ResolutionPhase as P


def _by_fragment_type(fragments: list[BaseFragment], fragment_type: str) -> list[BaseFragment]:
    return [f for f in fragments if isinstance(f, BaseFragment) and f.fragment_type == fragment_type]


def test_block_stores_inline_content() -> None:
    block = Block(label="block", content="Inline text")

    assert block.content == "Inline text"
    assert block.label == "block"


def test_get_concepts_returns_only_concepts() -> None:
    g = StoryGraph(label="test")
    block = Block(graph=g, label="parent")
    concept = Concept(graph=g, label="child", content="text")
    other = Block(graph=g, label="other")

    g.add_edge(block, concept)
    g.add_edge(block, other)

    concepts = block.get_concepts()

    assert concepts == [concept]


def test_get_choices_filters_by_availability() -> None:
    g = StoryGraph(label="test")
    start = Block(graph=g, label="start")
    left = Block(graph=g, label="left")
    right = Block(graph=g, label="right")

    locked = ChoiceEdge(graph=g, source_id=start.uid, destination_id=left.uid, label="locked")
    open_edge = ChoiceEdge(graph=g, source_id=start.uid, destination_id=right.uid, label="open")

    locked.predicate = lambda ns: ns.get("has_key", False)

    assert start.get_choices() == [locked, open_edge]
    assert start.get_choices(ns={"has_key": False}) == [open_edge]
    assert start.get_choices(ns={"has_key": True}) == [locked, open_edge]


def test_block_journal_renders_inline_content() -> None:
    g = StoryGraph(label="test")
    block = Block(graph=g, label="block", content="Inline text")

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    inline = _by_fragment_type(fragments, "block")
    assert len(inline) == 1
    assert "Inline text" in inline[0].content


def test_block_journal_renders_child_concepts() -> None:
    g = StoryGraph(label="test")
    block = Block(graph=g, label="block")
    first = Concept(graph=g, label="first", content="First")
    second = Concept(graph=g, label="second", content="Second")
    g.add_edge(block, first)
    g.add_edge(block, second)

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    concept_frags = _by_fragment_type(fragments, "concept")
    assert len(concept_frags) == 2
    contents = {f.content for f in concept_frags}
    assert {"First", "Second"} <= contents


def test_block_journal_renders_choice_menu() -> None:
    g = StoryGraph(label="test")
    start = Block(graph=g, label="start")
    left = Block(graph=g, label="left")
    right = Block(graph=g, label="right")
    Action(graph=g, source_id=start.uid, destination_id=left.uid, label="Left")
    Action(graph=g, source_id=start.uid, destination_id=right.uid, label="Right")

    frame = Frame(graph=g, cursor_id=start.uid)
    fragments = frame.run_phase(P.JOURNAL)

    menus = _by_fragment_type(fragments, "choice")
    assert len(menus) == 2
    assert menus[0].content == "Left"
    assert menus[1].content == "Right"


def test_block_with_concepts_and_choices_emits_all_fragments() -> None:
    g = StoryGraph(label="test")
    block = Block(graph=g, label="tavern", content="You enter the tavern.")
    smell = Concept(graph=g, label="smell", content="It smells of ale.")
    sound = Concept(graph=g, label="sound", content="Music plays softly.")
    g.add_edge(block, smell)
    g.add_edge(block, sound)

    bar = Block(graph=g, label="bar")
    corner = Block(graph=g, label="corner")
    Action(graph=g, source_id=block.uid, destination_id=bar.uid, label="Approach bar")
    Action(graph=g, source_id=block.uid, destination_id=corner.uid, label="Find corner")

    frame = Frame(graph=g, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    inline = _by_fragment_type(fragments, "block")
    menus = _by_fragment_type(fragments, "choice")
    concepts = _by_fragment_type(fragments, "concept")

    assert inline and concepts and menus

    inline_index = fragments.index(inline[0])
    first_concept_index = fragments.index(concepts[0])
    menu_index = fragments.index(menus[0])

    assert inline_index < menu_index < first_concept_index
