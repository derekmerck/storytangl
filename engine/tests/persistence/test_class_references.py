"""Qualified JSON class references preserve exact loaded identities."""

from __future__ import annotations

import pytest

from tangl.core import Graph, GraphFactory, Selector
from tangl.persistence import PersistenceManager
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.persistence.storage import InMemoryStorage
from tangl.persistence.structuring import StructuringHandler
from tangl.story import Scene as CardinalScene, World
from tangl.vm import Ledger

from pytest_helpers.qualified_scene_domain import Scene as DomainScene


@pytest.mark.parametrize("explicit_kind", [DomainScene, DomainScene.__fqn__()])
def test_explicit_domain_scene_and_cardinal_scene_coexist_after_json(
    explicit_kind: type[DomainScene] | str,
) -> None:
    suffix = "class" if isinstance(explicit_kind, type) else "dotted"
    world = World.from_script_data(script_data={
        "label": f"qualified_scene_{suffix}", "metadata": {"start_at": "intro.stage"},
        "globals": {"literal": {"class_name": DomainScene.__fqn__(), "has_kind": "Scene"}},
        "scenes": {"intro": {"blocks": {
            "stage": {"kind": explicit_kind, "content": "Domain scene."},
        }}},
    })
    graph = world.create_story(f"qualified_scene_{suffix}").graph
    cardinal = graph.find_one(Selector(label="intro"))
    custom = graph.find_one(Selector(label="stage"))
    assert type(cardinal) is CardinalScene
    assert type(custom) is DomainScene
    assert CardinalScene.__name__ == DomainScene.__name__ == "Scene"
    assert CardinalScene.__module__ != DomainScene.__module__

    payload = Json.deserialize(Json.serialize(graph.unstructure()))
    restored = Graph.structure(payload)
    assert type(restored.get(cardinal.uid)) is CardinalScene
    assert type(restored.get(custom.uid)) is DomainScene
    assert restored.get(custom.uid).domain_marker == "custom scene"
    assert restored.factory is world
    assert restored.locals["literal"] == graph.locals["literal"]
    assert restored.value_hash() == graph.value_hash()

    ledger = Ledger.from_graph(graph=graph)
    restored_ledger = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    assert type(restored_ledger.graph.get(cardinal.uid)) is CardinalScene
    assert type(restored_ledger.cursor) is DomainScene
    assert restored_ledger.graph.factory is world
    assert restored_ledger.graph.value_hash() == graph.value_hash()


def test_manager_registers_same_named_kinds_by_qualified_identity() -> None:
    storage = InMemoryStorage()
    manager = PersistenceManager(serializer=Json, structuring=StructuringHandler, storage=storage)
    cardinal = CardinalScene(label="cardinal")
    custom = DomainScene(label="domain")
    manager.save(cardinal)
    manager.save(custom)
    assert Json.deserialize(storage[cardinal.uid])["kind"] == CardinalScene.__fqn__()
    assert Json.deserialize(storage[custom.uid])["kind"] == DomainScene.__fqn__()
    assert manager.kind_map == {
        CardinalScene.__fqn__(): CardinalScene, DomainScene.__fqn__(): DomainScene,
    }

    reopened = PersistenceManager(serializer=Json, structuring=StructuringHandler, storage=storage)
    reopened.register_kinds(CardinalScene, DomainScene)
    assert type(reopened.load(cardinal.uid)) is CardinalScene
    assert type(reopened.load(custom.uid)) is DomainScene


def test_qualified_singleton_reference_uses_existing_manager_structuring() -> None:
    factory = GraphFactory(label="qualified_factory_reference")
    manager = PersistenceManager(
        serializer=Json, structuring=StructuringHandler, storage=InMemoryStorage(),
        kind_map={GraphFactory.__fqn__(): GraphFactory},
    )
    manager.save(factory)
    assert Json.deserialize(manager.storage[factory.uid]) == {
        "kind": GraphFactory.__fqn__(), "label": factory.label,
    }
    assert manager.load(factory.uid) is factory


def test_json_preserves_literal_class_like_strings_without_interpreting_them() -> None:
    payload = {
        "literal": "Scene", "qualified": DomainScene.__fqn__(),
        "nested": {"kind": DomainScene.__fqn__(), "has_kind": CardinalScene.__fqn__()},
    }
    assert Json.deserialize(Json.serialize(payload)) == payload
