"""Tests for :mod:`tangl.story.reference_domain.block`."""

from __future__ import annotations

from tangl.core import BaseFragment
from tangl.core import BaseFragment
from tangl.story.episode import Block, Action
from tangl.story.concepts import Concept
from tangl.story.story_graph import StoryGraph
from tangl.vm import ChoiceEdge, Frame, ResolutionPhase as P

from helpers.fragment_helpers import extract_fragments, extract_choices_from_block, extract_all_choices, extract_blocks_with_choices


# def _by_fragment_type(fragments: list[BaseFragment], fragment_type: str) -> list[BaseFragment]:
#     return [f for f in fragments if isinstance(f, BaseFragment) and f.fragment_type == fragment_type]


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

    inline = extract_fragments(fragments, "block")
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

    concept_frags = extract_fragments(fragments, "concept")
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

    menus = extract_all_choices(fragments)
    assert len(menus) == 2
    assert menus[0].content == "Left"
    assert menus[1].content == "Right"


def test_block_journal_includes_locked_choices() -> None:
    g = StoryGraph(label="test")
    start = Block(graph=g, label="start")
    open_block = Block(graph=g, label="open")
    locked_block = Block(graph=g, label="locked")
    start.locals["has_key"] = False

    Action(graph=g, source_id=start.uid, destination_id=open_block.uid, label="Open Door")
    Action(
        graph=g,
        source_id=start.uid,
        destination_id=locked_block.uid,
        label="Locked Door",
        conditions=["False"],
    )

    frame = Frame(graph=g, cursor_id=start.uid)
    fragments = frame.run_phase(P.JOURNAL)

    choice_fragments = extract_all_choices(fragments)
    assert len(choice_fragments) == 2

    active = [fragment for fragment in choice_fragments if fragment.active]
    inactive = [fragment for fragment in choice_fragments if not fragment.active]

    assert len(active) == 1
    assert len(inactive) == 1
    assert inactive[0].unavailable_reason is not None


