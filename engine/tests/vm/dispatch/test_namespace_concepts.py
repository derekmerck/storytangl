"""Tests for concept description namespace injection."""

from tangl.vm import Context
from tangl.story.story_graph import StoryGraph
from tangl.story.episode import Block


def test_concept_descriptions_available_in_namespace():
    """Concept descriptions are injected when provided on context."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block")

    ctx = Context(graph=graph, cursor_id=block.uid)
    ctx.set_concept_descriptions(
        {
            "dragon": "A fearsome red dragon",
            "treasure": "A pile of gold coins",
        }
    )

    ns = ctx.get_ns(block)

    assert ns["dragon"] == "A fearsome red dragon"
    assert ns["treasure"] == "A pile of gold coins"


def test_empty_concept_descriptions_do_not_pollute_namespace():
    """Namespace stays clean when context lacks concept descriptions."""

    graph = StoryGraph(label="test")
    block = Block(graph=graph, label="block")
    block.locals["dragon"] = "local dragon"

    ctx = Context(graph=graph, cursor_id=block.uid)

    ns = ctx.get_ns(block)

    assert ns["dragon"] == "local dragon"
