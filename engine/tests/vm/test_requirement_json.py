"""Known Entity kind references survive owning constructor-form JSON restoration."""

from __future__ import annotations

import pytest

from tangl.core import Graph, Selector
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import Action, InitMode, World
from tangl.vm import Ledger, TraversableNode
from tangl.vm.provision import Dependency, HasRequirement, Requirement
from tangl.vm.dispatch import on_gather_ns, on_update
from tangl.vm.system_handlers import apply_selected_edge_effects, contribute_runtime_baseline


@pytest.mark.parametrize("carrier_kind", [HasRequirement, Dependency])
def test_owned_requirement_kind_uses_existing_entity_class_lookup(carrier_kind: type) -> None:
    graph = Graph()
    provider = TraversableNode(label="target", registry=graph)
    carrier = carrier_kind(
        requirement=Requirement(has_kind=TraversableNode, has_identifier="target"), registry=graph,
    )
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    requirement = restored.get(carrier.uid).requirement
    assert requirement.has_kind is TraversableNode
    assert requirement.satisfied_by(restored.get(provider.uid))


def test_unresolved_lazy_destination_resolves_after_graph_and_ledger_json_restore() -> None:
    # VM tests isolate the global registry; opt into the real UPDATE policy.
    on_update(apply_selected_edge_effects)
    on_gather_ns(contribute_runtime_baseline)
    world = World.from_script_data(script_data={
        "label": "lazy_kind_json", "metadata": {"start_at": "intro.start"},
        "globals": {"count": 0, "literal": {"has_kind": "TraversableNode"}},
        "scenes": {"intro": {"blocks": {
            "start": {"actions": [{"text": "Continue", "successor": "end",
                                     "effects": ["graph.locals['count'] += 1"]}]},
            "end": {"content": "Done."},
        }}},
    })
    graph = world.create_story("lazy_kind_json", init_mode=InitMode.LAZY).graph
    restored_graph = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    ledger = Ledger.from_graph(graph=restored_graph, entry_id=restored_graph.initial_cursor_id)
    restored = Ledger.structure(Json.deserialize(Json.serialize(ledger.unstructure())))
    edge = restored.graph.find_one(Selector(has_kind=Action))
    dep = restored.graph.find_one(Selector(has_kind=Dependency, label="destination"))
    assert edge.successor is None and dep.provider is None
    assert dep.requirement.has_kind is TraversableNode
    assert restored.graph.locals["literal"] == {"has_kind": "TraversableNode"}
    restored.resolve_choice(edge.uid)
    assert restored.cursor.label == "end"
    assert edge.successor is dep.provider is restored.cursor
    assert restored.graph.locals["count"] == 1


def test_unknown_persisted_kind_is_not_imported_or_guessed() -> None:
    with pytest.raises(ValueError, match="Unknown requirement kind reference"):
        HasRequirement(requirement={"has_kind": "not_a_loaded_entity.Class"})
