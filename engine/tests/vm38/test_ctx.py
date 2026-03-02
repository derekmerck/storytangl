"""Contract tests for ``tangl.vm38.ctx`` protocols."""

from __future__ import annotations

from tangl.core38 import Graph
from tangl.core38.ctx import CoreCtx
from tangl.vm38.ctx import VmDispatchCtx, VmPhaseCtx, VmResolverCtx
from tangl.vm38.runtime.frame import PhaseCtx
from tangl.vm38.traversable import TraversableNode


def test_phase_ctx_satisfies_vm_protocols() -> None:
    graph = Graph()
    node = TraversableNode(label="n")
    graph.add(node)
    ctx = PhaseCtx(graph=graph, cursor_id=node.uid)

    assert isinstance(ctx, VmDispatchCtx)
    assert isinstance(ctx, VmResolverCtx)
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


def test_protocol_exports_are_importable_from_vm38_package() -> None:
    from tangl.vm38 import VmDispatchCtx as _VmDispatchCtx
    from tangl.vm38 import VmPhaseCtx as _VmPhaseCtx
    from tangl.vm38 import VmResolverCtx as _VmResolverCtx

    assert _VmDispatchCtx is VmDispatchCtx
    assert _VmResolverCtx is VmResolverCtx
    assert _VmPhaseCtx is VmPhaseCtx


def test_phase_ctx_exposes_with_subdispatch_context_manager() -> None:
    graph = Graph()
    node = TraversableNode(label="n")
    graph.add(node)
    ctx = PhaseCtx(graph=graph, cursor_id=node.uid)

    with ctx.with_subdispatch() as nested:
        assert nested is ctx
