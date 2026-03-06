"""Graph-to-dispatch bridge tests for link/unlink hooks."""

from __future__ import annotations

from types import SimpleNamespace

from tangl.core.behavior import BehaviorRegistry, DispatchLayer
from tangl.core.dispatch import on_link, on_unlink
from tangl.core.graph import Graph


class TestGraphDispatchHooks:
    def test_set_predecessor_with_ctx_fires_link_and_unlink(self, null_ctx) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        edge = graph.add_edge(None, b)

        events: list[str] = []
        on_link(func=lambda *, caller, node, **_: events.append(f"link:{node.label}"))
        on_unlink(func=lambda *, caller, node, **_: events.append(f"unlink:{node.label}"))

        edge.set_predecessor(a, _ctx=null_ctx)
        edge.set_predecessor(None, _ctx=null_ctx)
        assert events == ["link:a", "unlink:a"]

    def test_subgraph_add_member_chains_ctx_registry_and_inline(self) -> None:
        graph = Graph()
        node = graph.add_node(label="n")
        sg = graph.add_subgraph(label="s")

        events: list[str] = []
        app = BehaviorRegistry(default_dispatch_layer=DispatchLayer.APPLICATION)
        app.register(task="link", func=lambda *, caller, node, **_: events.append("ctx"))

        ctx = SimpleNamespace(
            get_registries=lambda: [app],
            get_inline_behaviors=lambda: [lambda *, caller, node, **_: events.append("inline")],
        )
        on_link(func=lambda *, caller, node, **_: events.append("global"))

        sg.add_member(node, _ctx=ctx)
        assert events == ["global", "ctx", "inline"]

    def test_add_edge_without_ctx_does_not_dispatch(self) -> None:
        graph = Graph()
        a = graph.add_node(label="a")
        b = graph.add_node(label="b")
        calls: list[str] = []
        on_link(func=lambda *, caller, node, **_: calls.append("called"))

        graph.add_edge(a, b)
        assert calls == []
