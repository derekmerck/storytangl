"""Contract tests for ``tangl.story.ctx`` protocols."""

from __future__ import annotations

from tangl.core import TemplateRegistry
from tangl.story.ctx import StoryRuntimeCtx
from tangl.story.fabula.materializer import _PrelinkCtx
from tangl.story.story_graph import StoryGraph
from tangl.vm.traversable import TraversableNode


def test_prelink_ctx_satisfies_story_runtime_protocol() -> None:
    graph = StoryGraph(locals={"gold": 7})
    node = TraversableNode(label="start")
    graph.add(node)
    templates = TemplateRegistry()

    ctx = _PrelinkCtx(
        graph=graph,
        template_registry=templates,
        cursor_id=node.uid,
        correlation_id="story-prelink",
        meta={"phase": "prelink"},
    )

    assert isinstance(ctx, StoryRuntimeCtx)
    assert ctx.cursor is node
    assert ctx.get_story_locals() == {"gold": 7}
    assert ctx.get_meta() == {"phase": "prelink"}
    assert ctx.get_location_entity_groups()
    assert ctx.get_template_scope_groups()
