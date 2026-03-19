"""Contract tests for ``tangl.story.ctx`` protocols."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.core import TemplateRegistry
from tangl.story.ctx import StoryRuntimeCtx
from tangl.story.fabula.materializer import StoryMaterializer, _PrelinkCtx
from tangl.story.story_graph import StoryGraph
from tangl.vm import Requirement
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx
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


def test_prelink_ctx_derives_child_phase_ctx() -> None:
    graph = StoryGraph(locals={"gold": 7})
    source = TraversableNode(label="start")
    child = TraversableNode(label="child")
    graph.add(source)
    graph.add(child)
    templates = TemplateRegistry()
    ctx = _PrelinkCtx(
        graph=graph,
        template_registry=templates,
        cursor_id=source.uid,
        correlation_id="story-prelink",
        meta={"phase": "prelink"},
    )

    child_ctx = ctx.derive(
        cursor_id=child.uid,
        meta_overrides={"request_ctx_path": "story.child"},
    )

    assert isinstance(child_ctx, PhaseCtx)
    assert child_ctx.graph is graph
    assert child_ctx.cursor_id == child.uid
    assert child_ctx.step == 0
    assert child_ctx.current_phase is ResolutionPhase.INIT
    assert child_ctx.correlation_id == "story-prelink"
    assert child_ctx.meta == {
        "phase": "prelink",
        "request_ctx_path": "story.child",
    }


def test_preview_requirement_contract_requires_typed_offer() -> None:
    graph = StoryGraph()
    materializer = StoryMaterializer()

    with pytest.raises(AttributeError, match="candidate"):
        materializer.preview_requirement_contract(
            requirement=Requirement(has_identifier="scene.child"),
            offer=SimpleNamespace(),
            graph=graph,
        )
