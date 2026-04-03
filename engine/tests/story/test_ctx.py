"""Contract tests for story runtime helpers built on ``PhaseCtx``."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from tangl.story.fabula.materializer import StoryMaterializer
from tangl.story.story_graph import StoryGraph
from tangl.vm import Requirement
from tangl.vm.resolution_phase import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.traversable import TraversableNode


def test_phase_ctx_covers_story_runtime_surface() -> None:
    graph = StoryGraph(locals={"gold": 7})
    node = TraversableNode(label="start")
    graph.add(node)
    ctx = PhaseCtx(
        graph=graph,
        cursor_id=node.uid,
        correlation_id="story-prelink",
        meta={"phase": "prelink"},
    )

    assert ctx.cursor is node
    assert graph.get_story_locals() == {"gold": 7}
    assert ctx.get_meta() == {"phase": "prelink"}
    assert ctx.get_location_entity_groups()


def test_materializer_preview_ctx_derives_from_phase_ctx() -> None:
    graph = StoryGraph(locals={"gold": 7})
    source = TraversableNode(label="start")
    graph.add(source)
    ctx = PhaseCtx(
        graph=graph,
        cursor_id=source.uid,
        correlation_id="story-prelink",
        meta={"phase": "prelink"},
    )
    materializer = StoryMaterializer()

    child_ctx = materializer._make_preview_requirement_ctx(
        graph=graph,
        request_ctx_path="story.child",
        _ctx=ctx,
    )

    assert isinstance(child_ctx, PhaseCtx)
    assert child_ctx.graph is graph
    assert child_ctx.cursor_id is None
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
