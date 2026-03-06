"""Replay MVP contract tests for vm38."""

from __future__ import annotations

from tangl.core import Graph
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
