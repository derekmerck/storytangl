"""Tests for journal state handling on Context."""

from tangl.vm import Context
from tangl.story.story_graph import StoryGraph
from tangl.story.episode import Block


def test_context_accepts_journal_state():
    """Frozen Context accepts journal state via dedicated setters."""

    graph = StoryGraph(label="test")
    start = Block(graph=graph, label="start")
    ctx = Context(graph=graph, cursor_id=start.uid)

    ctx.set_concept_descriptions({"dragon": "A red dragon"})
    ctx.set_current_content("test content")
    ctx.set_current_choices([])

    assert ctx.concept_descriptions == {"dragon": "A red dragon"}
    assert ctx.current_content == "test content"
    assert ctx.current_choices == []


def test_context_journal_state_defaults_to_none():
    """Journal state defaults to None on new Context instances."""

    graph = StoryGraph(label="test")
    start = Block(graph=graph, label="start")
    ctx = Context(graph=graph, cursor_id=start.uid)

    assert ctx.concept_descriptions is None
    assert ctx.current_content is None
    assert ctx.current_choices is None
