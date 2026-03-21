"""Replay MVP contract tests for vm."""

from __future__ import annotations

from tangl.core import EntityTemplate, Graph, Selector, TemplateRegistry
from tangl.vm import TraversableEdge, TraversableGraphFactory
from tangl.vm.replay import Event, OpEnum, Patch
from tangl.vm.traversable import TraversableNode


def test_patch_apply_to_updates_graph_entity() -> None:
    graph = Graph()
    node = TraversableNode(label="start", registry=graph)

    updated = node.evolve(label="updated")
    expected = Graph.structure(graph.unstructure())
    expected.remove(node.uid)
    expected.add(updated)
    patch = Patch(
        registry_id=graph.uid,
        initial_registry_value_hash=graph.value_hash(),
        final_registry_value_hash=expected.value_hash(),
        events=[
            Event(
                operation=OpEnum.UPDATE,
                item_id=node.uid,
                value=updated.unstructure(),
            )
        ],
    )

    patch.apply_to(graph)
    assert graph.get(node.uid).label == "updated"


class RefTraversableEdge(TraversableEdge):
    """Test edge exposing factory predecessor/successor refs."""

    predecessor_ref: bytes | None = None
    successor_ref: str | None = None


class ReplayFactoryTestDouble(TraversableGraphFactory):
    """Test-local singleton subclass used for replay factory coverage."""


def test_patch_apply_to_updates_factory_built_traversable_graph() -> None:
    ReplayFactoryTestDouble.clear_instances()
    try:
        template_registry = TemplateRegistry(label="replay_factory_templates")
        start = EntityTemplate(
            label="start",
            payload=TraversableNode(label="start"),
            registry=template_registry,
        )
        updated = EntityTemplate(
            label="updated",
            payload=TraversableNode(label="updated"),
            registry=template_registry,
        )
        EntityTemplate(
            label="start.go",
            payload=RefTraversableEdge(
                label="start_go",
                predecessor_ref=start.content_hash(),
                successor_ref="updated",
            ),
            registry=template_registry,
        )

        factory = ReplayFactoryTestDouble(label="replay_factory", templates=template_registry)
        graph = factory.materialize_graph()
        node = graph.find_node(Selector(label="start"))
        assert isinstance(node, TraversableNode)

        replacement = node.evolve(label="retitled")
        expected = type(graph).structure(graph.unstructure())
        expected.add(replacement)
        patch = Patch(
            registry_id=graph.uid,
            initial_registry_value_hash=graph.value_hash(),
            final_registry_value_hash=expected.value_hash(),
            events=[
                Event(
                    operation=OpEnum.UPDATE,
                    item_id=node.uid,
                    value=replacement.unstructure(),
                )
            ],
        )

        patch.apply_to(graph)
        assert graph.get(node.uid).label == "retitled"
    finally:
        ReplayFactoryTestDouble.clear_instances()
