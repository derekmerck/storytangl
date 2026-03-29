"""Contract tests for ``tangl.vm.ctx`` protocols."""

from __future__ import annotations

from tangl.core import Graph
from tangl.core.ctx import CoreCtx
from tangl.vm.ctx import VmPhaseCtx
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.traversable import TraversableNode


def test_phase_ctx_satisfies_vm_protocol() -> None:
    graph = Graph()
    node = TraversableNode(label="n")
    graph.add(node)
    ctx = PhaseCtx(graph=graph, cursor_id=node.uid)

    assert isinstance(ctx, VmPhaseCtx)
    assert isinstance(ctx, CoreCtx)


def test_phase_ctx_exposes_core_meta_surface() -> None:
    graph = Graph()
    node = TraversableNode(label="n")
    graph.add(node)
    ctx = PhaseCtx(
        graph=graph,
        cursor_id=node.uid,
        correlation_id="corr-1",
        meta={"k": "v"},
    )

    assert ctx.correlation_id == "corr-1"
    assert ctx.get_meta() == {"k": "v"}


def test_protocol_exports_are_importable_from_vm_package() -> None:
    from tangl.vm import VmPhaseCtx as _VmPhaseCtx

    assert _VmPhaseCtx is VmPhaseCtx


def test_phase_ctx_exposes_with_subdispatch_context_manager() -> None:
    graph = Graph()
    node = TraversableNode(label="n")
    graph.add(node)
    ctx = PhaseCtx(graph=graph, cursor_id=node.uid)

    with ctx.with_subdispatch() as nested:
        assert nested is ctx


def test_phase_ctx_isolates_result_pipe_for_subdispatch() -> None:
    graph = Graph()
    node = TraversableNode(label="n")
    graph.add(node)
    ctx = PhaseCtx(graph=graph, cursor_id=node.uid)

    ctx.push_result("outer")
    assert ctx.results == ["outer"]

    with ctx.with_subdispatch() as nested:
        assert nested.results == []
        nested.push_result("inner")
        assert nested.results == ["inner"]

    assert ctx.results == ["outer"]
