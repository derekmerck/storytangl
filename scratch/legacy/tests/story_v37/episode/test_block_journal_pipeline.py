"""Test full journal pipeline end-to-end."""
from __future__ import annotations

import pytest

from tangl.journal.content import ContentFragment
from tangl.journal.discourse import AttributedFragment
from tangl.story.concepts import Concept
from tangl.story.episode import Action, Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import Frame, ResolutionPhase as P


def test_full_pipeline_static_block():
    """Static block should emit rendered content and a single choice."""

    graph = StoryGraph(label="test")

    start = Block(graph=graph, label="start", content="You are in a room.")
    end = Block(graph=graph, label="end")
    Action(graph=graph, source_id=start.uid, destination_id=end.uid, label="Leave")

    frame = Frame(graph=graph, cursor_id=start.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content_frags = [frag for frag in fragments if isinstance(frag, ContentFragment)]
    assert len(content_frags) >= 1
    assert "You are in a room." in content_frags[0].content

    choice_frags = [
        frag for frag in fragments if getattr(frag, "fragment_type", None) == "choice"
    ]
    assert len(choice_frags) == 1
    assert choice_frags[0].content == "Leave"


def test_full_pipeline_with_concepts():
    """Concept descriptions should enrich templates without emitting fragments."""

    graph = StoryGraph(label="test")

    block = Block(graph=graph, label="block", content="You see {{ dragon }}.")
    dragon = Concept(graph=graph, label="dragon", content="a red dragon")
    graph.add_edge(block, dragon)

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content_frags = [frag for frag in fragments if isinstance(frag, ContentFragment)]
    assert any("a red dragon" in frag.content for frag in content_frags)

    concept_frags = [
        frag for frag in fragments if getattr(frag, "fragment_type", None) == "concept"
    ]
    assert len(concept_frags) == 0


def test_full_pipeline_with_dialog():
    """Dialog syntax should become attributed fragments."""

    graph = StoryGraph(label="test")

    block = Block(
        graph=graph,
        label="block",
        content="> [!dialog] Guard\n> Stop right there!",
    )

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    dialog_frags = [frag for frag in fragments if isinstance(frag, AttributedFragment)]
    assert len(dialog_frags) >= 1
    assert dialog_frags[0].content == "Stop right there!"


def test_full_pipeline_flat_output():
    """Journal output should be a flat list without block grouping."""

    graph = StoryGraph(label="test")

    block = Block(graph=graph, label="block", content="Test")
    next_block = Block(graph=graph, label="next")
    Action(graph=graph, source_id=block.uid, destination_id=next_block.uid, label="Go")

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    assert isinstance(fragments, list)

    from tangl.journal.discourse import BlockFragment

    block_frags = [frag for frag in fragments if isinstance(frag, BlockFragment)]
    assert len(block_frags) == 0


def test_empty_block_empty_output():
    """Blocks without content or choices should not emit content/choice fragments."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="empty", content="")

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content_frags = [frag for frag in fragments if isinstance(frag, ContentFragment)]
    choice_frags = [
        frag for frag in fragments if getattr(frag, "fragment_type", None) == "choice"
    ]

    assert len(content_frags) == 0
    assert len(choice_frags) == 0
