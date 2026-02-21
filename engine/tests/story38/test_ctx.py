"""Contract tests for ``tangl.story38.ctx`` protocols."""

from __future__ import annotations

from tangl.core38 import TemplateRegistry
from tangl.story38.ctx import StoryRuntimeCtx
from tangl.story38.fabula.materializer import _PrelinkCtx
from tangl.story38.story_graph import StoryGraph38
from tangl.vm38.traversable import TraversableNode


def test_prelink_ctx_satisfies_story_runtime_protocol() -> None:
    graph = StoryGraph38(locals={"gold": 7})
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
