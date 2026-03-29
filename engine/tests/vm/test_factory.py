"""Contract tests for ``tangl.vm.factory``.

Organized by concept:
- TraversableGraphFactory materialization and entry resolution
- Traversal contract validation on factory-built graphs
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from tangl.core import EntityTemplate, Graph, Node, Selector, TemplateRegistry
from tangl.core.template import TemplateGroup
from tangl.vm import TraversableEdge, TraversableGraph, TraversableGraphFactory, TraversableNode


class RefTraversableEdge(TraversableEdge):
    """Test edge exposing the refs required by ``GraphFactory``."""

    predecessor_ref: bytes | None = None
    successor_ref: str | None = None


class TraversableGraphFactoryTestDouble(TraversableGraphFactory):
    """Test-local singleton subclass used to isolate VM factory instances."""


class _TemplateSubset:
    """Minimal read-only template subset for seed-graph tests."""

    def __init__(self, registry: TemplateRegistry, selected_labels: set[str]) -> None:
        self.registry = registry
        self.selected_labels = selected_labels

    def _values(self):
        return [
            value
            for value in self.registry.values()
            if getattr(value, "label", None) in self.selected_labels
        ]

    def find_all(self, selector: Selector | None = None, *, sort_key=None):
        values = self._values()
        if selector is not None:
            values = list(selector.filter(values))
        if sort_key is not None:
            values = sorted(values, key=sort_key)
        return values


@pytest.fixture(autouse=True)
def clear_factories() -> None:
    TraversableGraphFactoryTestDouble.clear_instances()
    yield
    TraversableGraphFactoryTestDouble.clear_instances()


def _group_template(*, registry: TemplateRegistry, label: str, **payload_kwargs) -> TemplateGroup:
    return TemplateGroup(
        label=label,
        payload=TraversableNode(label=label.rsplit(".", 1)[-1], **payload_kwargs),
        registry=registry,
    )


def _node_template(
    *,
    registry: TemplateRegistry,
    label: str,
    kind: type[Node] = TraversableNode,
) -> EntityTemplate:
    return EntityTemplate(
        label=label,
        payload=kind(label=label.rsplit(".", 1)[-1]),
        registry=registry,
    )


def _edge_template(
    *,
    registry: TemplateRegistry,
    label: str,
    predecessor_templ: EntityTemplate,
    successor_ref: str,
) -> EntityTemplate:
    return EntityTemplate(
        label=label,
        payload=RefTraversableEdge(
            label=label.rsplit(".", 1)[-1],
            predecessor_ref=predecessor_templ.content_hash(),
            successor_ref=successor_ref,
        ),
        registry=registry,
    )


class TestTraversableGraphFactoryMaterialize:
    """Tests for traversal-ready graph materialization."""

    def test_materialize_graph_returns_traversable_graph_and_sets_initial_cursor(self) -> None:
        template_registry = TemplateRegistry(label="vm_factory_templates")
        root = _group_template(registry=template_registry, label="root")
        chapter = _group_template(registry=template_registry, label="root.chapter")
        root_start = _node_template(registry=template_registry, label="root.start")
        nested_start = _node_template(registry=template_registry, label="root.chapter.start")

        root.add_child(chapter)
        root.add_child(root_start)
        chapter.add_child(nested_start)

        factory = TraversableGraphFactoryTestDouble(
            label="vm_factory",
            templates=template_registry,
        )
        graph = factory.materialize_graph()

        assert isinstance(graph, TraversableGraph)
        assert graph.factory is factory
        assert graph.initial_cursor_id is not None

        entry = graph.get(graph.initial_cursor_id)
        assert isinstance(entry, TraversableNode)
        assert entry.has_path("root.start")

    def test_materialize_graph_rejects_plain_core_graph_instances(self) -> None:
        template_registry = TemplateRegistry(label="vm_plain_graph_templates")
        _node_template(registry=template_registry, label="start")

        factory = TraversableGraphFactoryTestDouble(
            label="vm_plain_graph_factory",
            templates=template_registry,
        )
        with pytest.raises(TypeError, match="requires a TraversableGraph"):
            factory.materialize_graph(graph=Graph())

    def test_missing_entry_raises_deterministically(self) -> None:
        template_registry = TemplateRegistry(label="vm_missing_entry_templates")
        _node_template(registry=template_registry, label="intro")

        factory = TraversableGraphFactoryTestDouble(
            label="vm_missing_entry_factory",
            templates=template_registry,
        )
        with pytest.raises(ValueError, match="could not resolve an initial entry cursor"):
            factory.materialize_graph()

    def test_non_traversable_entry_raises_deterministically(self) -> None:
        template_registry = TemplateRegistry(label="vm_non_traversable_entry_templates")
        _node_template(registry=template_registry, label="start", kind=Node)

        factory = TraversableGraphFactoryTestDouble(
            label="vm_non_traversable_entry_factory",
            templates=template_registry,
        )
        with pytest.raises(TypeError, match="must be a TraversableNode"):
            factory.materialize_graph()

    def test_invalid_container_contracts_raise_after_materialization(self) -> None:
        template_registry = TemplateRegistry(label="vm_invalid_contract_templates")
        scene = _group_template(
            registry=template_registry,
            label="scene",
            source_id=uuid4(),
            sink_id=uuid4(),
        )
        start = _node_template(registry=template_registry, label="scene.start")
        finish = _node_template(registry=template_registry, label="scene.finish")
        edge = _edge_template(
            registry=template_registry,
            label="scene.go",
            predecessor_templ=start,
            successor_ref="finish",
        )

        scene.add_child(start)
        scene.add_child(finish)
        scene.add_child(edge)

        factory = TraversableGraphFactoryTestDouble(
            label="vm_invalid_contract_factory",
            templates=template_registry,
        )
        with pytest.raises(ValueError, match="Traversal contract validation failed"):
            factory.materialize_graph()

    def test_materialize_seed_graph_materializes_only_selected_templates(self) -> None:
        template_registry = TemplateRegistry(label="vm_seed_templates")
        scene = _group_template(registry=template_registry, label="scene")
        start = _node_template(registry=template_registry, label="scene.start")
        later = _node_template(registry=template_registry, label="scene.later")

        scene.add_child(start)
        scene.add_child(later)

        factory = TraversableGraphFactoryTestDouble(
            label="vm_seed_factory",
            templates=template_registry,
        )
        graph = factory.materialize_seed_graph(
            template_groups=[
                _TemplateSubset(
                    template_registry,
                    selected_labels={"scene", "scene.start"},
                )
            ]
        )

        labels = {getattr(item, "label", None) for item in graph.values()}
        assert labels >= {"scene", "start"}
        assert "later" not in labels
        assert graph.initial_cursor_id is not None
