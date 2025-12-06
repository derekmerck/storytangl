from __future__ import annotations

from tangl.vm import Frame, ResolutionPhase as P
from tangl.story.concepts import Concept
from tangl.story.episode import Block
from tangl.story.story_graph import StoryGraph


def test_concepts_enrich_namespace_not_output() -> None:
    """Concept descriptions populate the namespace but do not emit fragments."""

    graph = StoryGraph(label="test")

    block = Block(graph=graph, label="block", content="")
    dragon = Concept(graph=graph, label="dragon", content="a red dragon")
    treasure = Concept(graph=graph, label="treasure", content="gold coins")

    graph.add_edge(block, dragon)
    graph.add_edge(block, treasure)

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    concept_frags = [
        fragment
        for fragment in fragments
        if getattr(fragment, "fragment_type", None) == "concept"
    ]
    assert concept_frags == []

    assert frame.context.concept_descriptions is not None
    assert frame.context.concept_descriptions["dragon"] == "a red dragon"
    assert frame.context.concept_descriptions["treasure"] == "gold coins"


def test_concepts_available_in_block_templates() -> None:
    """Block content templates can reference concept descriptions."""

    graph = StoryGraph(label="test")

    block = Block(
        graph=graph,
        label="block",
        content="You see {{ dragon }} guarding {{ treasure }}.",
    )
    dragon = Concept(graph=graph, label="dragon", content="a fearsome red dragon")
    treasure = Concept(graph=graph, label="treasure", content="a pile of gold coins")

    graph.add_edge(block, dragon)
    graph.add_edge(block, treasure)

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    content_frags = [
        fragment
        for fragment in fragments
        if getattr(fragment, "fragment_type", None) == "content"
    ]
    assert content_frags

    content_text = content_frags[0].content
    assert "a fearsome red dragon" in content_text
    assert "a pile of gold coins" in content_text
    assert "{{ dragon }}" not in content_text
    assert "{{ treasure }}" not in content_text


def test_empty_concepts_skip_namespace() -> None:
    """Concepts without content are omitted from namespace descriptions."""

    graph = StoryGraph(label="test")

    block = Block(graph=graph, label="block", content="test")
    empty_concept = Concept(graph=graph, label="empty", content="")

    graph.add_edge(block, empty_concept)

    frame = Frame(graph=graph, cursor_id=block.uid)
    frame.run_phase(P.JOURNAL)

    assert not frame.context.concept_descriptions
