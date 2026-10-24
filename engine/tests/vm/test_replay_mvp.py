"""Replay MVP contract tests for vm."""

from __future__ import annotations

from uuid import UUID

import pytest

from tangl.core import EntityTemplate, Graph, Node, Selector, TemplateRegistry
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.vm import Ledger, TraversableEdge, TraversableGraphFactory
from tangl.vm.replay import CheckpointRecord, Event, OpEnum, Patch, get_replay_engine
from tangl.vm.traversable import TraversableNode


def assert_same_ordered_graph(actual: Graph, expected: Graph) -> None:
    assert list(actual.members) == list(expected.members)
    assert all(actual.get(uid).value_hash() == expected.get(uid).value_hash()
               for uid in expected.members)
    assert actual.value_hash() == expected.value_hash()
    assert actual.find_one(Selector()).label == expected.find_one(Selector()).label


@pytest.mark.parametrize("existing", ["empty", "survivors", "mixed"])
def test_checked_diff_preserves_new_member_insertion_order(existing: str) -> None:
    before = Graph()
    if existing != "empty":
        before.add(Node(uid=UUID(int=8), label="survivor_first"))
        before.add(Node(uid=UUID(int=7), label="remove_me"))
        before.add(Node(uid=UUID(int=6), label="survivor_last"))
    after = Graph.structure(before.unstructure())
    if existing == "mixed":
        after.remove(UUID(int=7))
        after.add(after.get(UUID(int=8)).evolve(label="updated_first"))
    # Explicit identities are reverse to insertion order, not random UUID luck.
    after.add(Node(uid=UUID(int=2), label="new_first"))
    after.add(Node(uid=UUID(int=1), label="new_second"))
    engine = get_replay_engine("diff_v1")
    delta = engine.build_delta(before_graph=before, after_graph=after)

    replayed = engine.apply_delta(graph=Graph.structure(before.unstructure()), delta=delta)

    assert_same_ordered_graph(replayed, after)
    assert [event.item_id for event in delta.events if event.operation is OpEnum.CREATE] == [
        UUID(int=2), UUID(int=1),
    ]


@pytest.mark.parametrize("json_store", [False, True])
def test_checkpoint_and_multiple_patches_preserve_order_through_ledger_restore(
    json_store: bool,
) -> None:
    before = Graph()
    entry = TraversableNode(uid=UUID(int=9), label="entry", registry=before)
    ledger = Ledger.from_graph(before, entry_id=entry.uid)
    first = Graph.structure(before.unstructure())
    first.add(Node(uid=UUID(int=2), label="first"))
    first.add(Node(uid=UUID(int=1), label="second"))
    second = Graph.structure(first.unstructure())
    second.remove(UUID(int=2))
    second.add(second.get(UUID(int=1)).evolve(label="updated_second"))
    second.add(Node(uid=UUID(int=6), label="third"))
    second.add(Node(uid=UUID(int=3), label="fourth"))
    engine = get_replay_engine(ledger.replay_algorithm_id)
    ledger.output_stream.append(engine.build_delta(before_graph=before, after_graph=first))
    ledger.output_stream.append(engine.build_delta(before_graph=first, after_graph=second))
    data = ledger.unstructure()
    if json_store:
        data = Json.deserialize(Json.serialize(data))
    restored = Ledger.structure(data)
    checkpoint = next(Selector(has_kind=CheckpointRecord).filter(restored.output_stream))
    patches = list(Selector(has_kind=Patch).filter(restored.output_stream))

    replayed = engine.restore_checkpoint(checkpoint)
    assert len(patches) == 2
    replayed = engine.apply_delta(graph=replayed, delta=patches[0])
    assert_same_ordered_graph(replayed, first)
    replayed = engine.apply_delta(graph=replayed, delta=patches[1])
    assert_same_ordered_graph(replayed, second)


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
