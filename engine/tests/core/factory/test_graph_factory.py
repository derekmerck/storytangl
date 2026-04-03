"""Contract tests for ``tangl.core.factory``."""

from __future__ import annotations

import pytest

from tangl.core import (
    EntityTemplate,
    Graph,
    GraphFactory,
    HierarchicalNode,
    Node,
    Selector,
    TemplateRegistry,
)
from tangl.core.graph import Edge
from tangl.core.template import TemplateGroup


class RefEdge(Edge):
    """Test edge exposing the refs required by ``GraphFactory``."""

    predecessor_ref: bytes | None = None
    successor_ref: str | None = None


class GraphFactoryTestDouble(GraphFactory):
    """Test-local singleton subclass used to isolate factory instances."""


@pytest.fixture(autouse=True)
def clear_factories() -> None:
    GraphFactoryTestDouble.clear_instances()
    yield
    GraphFactoryTestDouble.clear_instances()


def _template_group(*, registry, label: str) -> TemplateGroup:
    return TemplateGroup(
        label=label,
        payload=HierarchicalNode(label=label.rsplit(".", 1)[-1]),
        registry=registry,
    )


def _node_template(*, registry, label: str) -> EntityTemplate:
    return EntityTemplate(label=label, payload=Node(label=label.rsplit(".", 1)[-1]), registry=registry)


def _edge_template(
    *,
    registry,
    label: str,
    predecessor_templ: EntityTemplate,
    successor_ref: str | None,
) -> EntityTemplate:
    return EntityTemplate(
        label=label,
        payload=RefEdge(
            label=label.rsplit(".", 1)[-1],
            predecessor_ref=predecessor_templ.content_hash(),
            successor_ref=successor_ref,
        ),
        registry=registry,
    )


class TestGraphFactoryMaterialize:
    """Tests for deterministic core graph materialization."""

    def test_materialize_graph_returns_graph_and_attaches_nested_members(self) -> None:
        template_registry = TemplateRegistry(label="tree_templates")
        root = _template_group(registry=template_registry, label="root")
        chapter = _template_group(registry=template_registry, label="root.chapter")
        start = _node_template(registry=template_registry, label="root.start")
        finish = _node_template(registry=template_registry, label="root.chapter.finish")

        root.add_child(chapter)
        root.add_child(start)
        chapter.add_child(finish)

        factory = GraphFactoryTestDouble(label="tree_factory", templates=template_registry)
        graph = factory.materialize_graph()

        root_group = graph.find_node(Selector(label="root"))
        chapter_group = graph.find_node(Selector(label="chapter"))
        start_node = graph.find_node(Selector(label="start"))
        finish_node = graph.find_node(Selector(label="finish"))

        assert graph.factory is factory
        assert root_group is not None
        assert chapter_group is not None
        assert start_node is not None
        assert finish_node is not None
        assert list(root_group.members()) == [chapter_group, start_node]
        assert list(chapter_group.members()) == [finish_node]

    def test_graph_roundtrip_preserves_factory_singleton_identity(self) -> None:
        template_registry = TemplateRegistry(label="roundtrip_templates")
        root = _template_group(registry=template_registry, label="root")
        start = _node_template(registry=template_registry, label="root.start")
        root.add_child(start)

        factory = GraphFactoryTestDouble(label="roundtrip_factory", templates=template_registry)
        graph = factory.materialize_graph()

        restored = Graph.structure(graph.unstructure())

        assert restored.factory is factory
        assert restored.get_authorities() == [factory.dispatch]

    def test_predecessor_binding_uses_template_provenance(self) -> None:
        template_registry = TemplateRegistry(label="edge_templates")
        root = _template_group(registry=template_registry, label="root")
        start = _node_template(registry=template_registry, label="root.start")
        finish = _node_template(registry=template_registry, label="root.finish")
        edge = _edge_template(
            registry=template_registry,
            label="root.go",
            predecessor_templ=start,
            successor_ref="finish",
        )

        root.add_child(start)
        root.add_child(finish)
        root.add_child(edge)

        graph = GraphFactoryTestDouble(label="edge_factory", templates=template_registry).materialize_graph()
        wired_edge = graph.find_edge(Selector(label="go"))
        start_node = graph.find_node(Selector(label="start"))
        finish_node = graph.find_node(Selector(label="finish"))

        assert wired_edge is not None
        assert start_node is not None
        assert finish_node is not None
        assert wired_edge.predecessor is start_node
        assert wired_edge.successor is finish_node
        assert wired_edge.predecessor.templ_hash == start.content_hash()

    def test_successor_resolution_prefers_nearest_connected_candidate(self) -> None:
        template_registry = TemplateRegistry(label="nearest_templates")
        shared = _template_group(registry=template_registry, label="shared")
        branch = _template_group(registry=template_registry, label="shared.branch")
        isolated = _template_group(registry=template_registry, label="isolated")
        start = _node_template(registry=template_registry, label="shared.branch.start")
        connected_exit = _node_template(registry=template_registry, label="shared.exit")
        disconnected_exit = _node_template(registry=template_registry, label="isolated.exit")
        edge = _edge_template(
            registry=template_registry,
            label="shared.branch.go",
            predecessor_templ=start,
            successor_ref="exit",
        )

        shared.add_child(branch)
        branch.add_child(start)
        branch.add_child(edge)
        shared.add_child(connected_exit)
        isolated.add_child(disconnected_exit)

        graph = GraphFactoryTestDouble(
            label="nearest_factory",
            templates=template_registry,
        ).materialize_graph()
        wired_edge = graph.find_edge(Selector(label="go"))
        connected_node = next(
            node for node in graph.find_nodes(Selector(label="exit")) if node.has_path("shared.exit")
        )

        assert wired_edge is not None
        assert wired_edge.successor is connected_node

    def test_equal_distance_successors_raise_ambiguity(self) -> None:
        template_registry = TemplateRegistry(label="tie_templates")
        root = _template_group(registry=template_registry, label="root")
        start = _node_template(registry=template_registry, label="root.start")
        left_exit = _node_template(registry=template_registry, label="root.exit_left")
        right_exit = _node_template(registry=template_registry, label="root.exit_right")
        left_exit.payload.label = "exit"
        right_exit.payload.label = "exit"
        left_exit.payload.tags.add("left")
        right_exit.payload.tags.add("right")
        edge = _edge_template(
            registry=template_registry,
            label="root.choice",
            predecessor_templ=start,
            successor_ref="exit",
        )

        root.add_child(start)
        root.add_child(left_exit)
        root.add_child(right_exit)
        root.add_child(edge)

        factory = GraphFactoryTestDouble(label="tie_factory", templates=template_registry)
        with pytest.raises(ValueError, match="resolved ambiguously"):
            factory.materialize_graph()

    def test_ambiguous_link_resolution_stops_later_edge_wiring(self) -> None:
        template_registry = TemplateRegistry(label="abort_templates")
        root = _template_group(registry=template_registry, label="root")
        start = _node_template(registry=template_registry, label="root.start")
        left_exit = _node_template(registry=template_registry, label="root.exit_left")
        right_exit = _node_template(registry=template_registry, label="root.exit_right")
        done = _node_template(registry=template_registry, label="root.done")
        left_exit.payload.label = "exit"
        right_exit.payload.label = "exit"
        left_exit.payload.tags.add("left")
        right_exit.payload.tags.add("right")
        ambiguous_edge = _edge_template(
            registry=template_registry,
            label="root.ambiguous",
            predecessor_templ=start,
            successor_ref="exit",
        )
        later_edge = _edge_template(
            registry=template_registry,
            label="root.later",
            predecessor_templ=start,
            successor_ref="done",
        )

        root.add_child(start)
        root.add_child(left_exit)
        root.add_child(right_exit)
        root.add_child(done)
        root.add_child(ambiguous_edge)
        root.add_child(later_edge)

        factory = GraphFactoryTestDouble(label="abort_factory", templates=template_registry)
        graph = Graph()
        with pytest.raises(ValueError, match="resolved ambiguously"):
            factory.materialize_graph(graph=graph)

        assert graph.find_edge(Selector(label="ambiguous")) is None
        assert graph.find_edge(Selector(label="later")) is None

    @pytest.mark.parametrize(
        ("mutator", "message"),
        [
            (lambda edge: setattr(edge.payload, "predecessor_ref", None), "missing predecessor_ref"),
            (lambda edge: setattr(edge.payload, "predecessor_ref", b"missing"), "predecessor template"),
            (lambda edge: setattr(edge.payload, "successor_ref", None), "missing successor_ref"),
            (lambda edge: setattr(edge.payload, "successor_ref", "missing"), "did not resolve"),
        ],
    )
    def test_invalid_edge_refs_raise_precise_errors(self, mutator, message: str) -> None:
        template_registry = TemplateRegistry(label="invalid_edge_templates")
        root = _template_group(registry=template_registry, label="root")
        start = _node_template(registry=template_registry, label="root.start")
        finish = _node_template(registry=template_registry, label="root.finish")
        edge = _edge_template(
            registry=template_registry,
            label="root.broken",
            predecessor_templ=start,
            successor_ref="finish",
        )

        mutator(edge)
        root.add_child(start)
        root.add_child(finish)
        root.add_child(edge)

        factory = GraphFactoryTestDouble(
            label=f"invalid_factory_{message}",
            templates=template_registry,
        )
        with pytest.raises(ValueError, match=message):
            factory.materialize_graph()

    def test_get_entry_cursor_prefers_shallowest_match(self) -> None:
        template_registry = TemplateRegistry(label="entry_templates")
        root = _template_group(registry=template_registry, label="root")
        chapter = _template_group(registry=template_registry, label="root.chapter")
        shallow_start = _node_template(registry=template_registry, label="root.start")
        deep_start = _node_template(registry=template_registry, label="root.chapter.start")

        root.add_child(chapter)
        root.add_child(shallow_start)
        chapter.add_child(deep_start)

        factory = GraphFactoryTestDouble(label="entry_factory", templates=template_registry)
        graph = factory.materialize_graph()

        entry = factory.get_entry_cursor(graph)
        assert entry is not None
        assert entry.label == "start"
        assert entry.has_path("root.start")
