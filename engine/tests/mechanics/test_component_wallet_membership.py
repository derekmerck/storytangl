"""Graph-owned assembly membership and detached adoption."""

from typing import ClassVar

import pytest
from pydantic import Field, model_validator

from tangl.core import Graph, Node
from tangl.mechanics.assembly import Component, ComponentFacet, ComponentManager, Slot
from tangl.mechanics.assembly.examples.vehicle import Vehicle, VehicleComponent
from tangl.mechanics.transaction import (
    AssetMoveCommitment, CallbackCommitment, CatalogAssetCommitment, ComponentAssignmentCommitment,
    ComponentSlotAssetHolder, TransactionOffer,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import StoryGraph


class Parts(ComponentManager[Component]):
    slots: ClassVar[dict[str, Slot]] = {
        "left": Slot.for_type("left", Component, max_count=2),
        "right": Slot.for_type("right", Component, max_count=2),
        "empty": Slot.for_type("empty", Component),
    }


class Machine(Node):
    parts: Parts = Field(default_factory=Parts, json_schema_extra={"include": True, "unstructurable": True})

    @model_validator(mode="after")
    def bind_parts(self):
        self.parts.bind_owner(self)
        return self


def test_slot_groups_roundtrip_and_preflight_are_pure() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    part = Component(label="light", registry=graph, facets=[ComponentFacet(channel="light", facet_type="giver")])
    foreign = Component(label="foreign", registry=Graph())
    before = graph.value_hash(), len(graph.members)
    assert owner.parts.get_slot("left") == []
    assert owner.parts.can_assign("left", part)[0]
    assert not owner.parts.can_assign("left", foreign)[0]
    assert (graph.value_hash(), len(graph.members)) == before

    owner.parts.assign("left", part)
    owner.parts.assign("right", part)
    empty = owner.parts.prepare_slot("empty")
    before = graph.value_hash(), len(graph.members)
    assert not owner.parts.can_assign("left", part)[0]
    with pytest.raises(ValueError):
        owner.parts.assign("left", part)
    assert (graph.value_hash(), len(graph.members)) == before
    assert part.parent is None
    facets = owner.parts.component_facets(channel="light")
    assert [(f.source_id, f.subject_id) for f in facets] == [(str(part.uid), "left"), (str(part.uid), "right")]

    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    copy = restored.get(owner.uid)
    restored_part = restored.get(part.uid)
    assert copy.parts.owner is copy
    assert copy.parts.slot_wallet_ids == owner.parts.slot_wallet_ids
    assert copy.parts.slot_wallet("empty") is restored.get(empty.uid)
    assert copy.parts.get_slot("left") == [restored_part]
    assert copy.parts.get_slot("right") == [restored_part]
    assert restored.value_hash() == graph.value_hash()


def test_detached_adoption_discards_pending_objects() -> None:
    owner = Machine()
    part = Component(label="part")
    owner.parts.assign("left", part)
    graph = Graph()
    graph.add(owner)
    owner.parts.bind_owner(owner)
    assert owner.parts.get_slot("left") == [part]
    assert graph.get(part.uid) is part
    assert not owner.parts.assignments and not owner.parts._component_cache


def test_missing_assigned_component_fails_visibly() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    part = Component(label="part", registry=graph)
    owner.parts.assign("left", part)
    graph.remove(part.uid)
    with pytest.raises(KeyError, match="missing"):
        owner.parts.get_slot("left")


def test_detached_adoption_rejects_foreign_part_without_partial_registration() -> None:
    owner = Machine()
    fresh = Component(label="fresh")
    foreign = Component(label="foreign", registry=Graph())
    owner.parts.assign("left", fresh)
    owner.parts.assign("right", foreign)
    graph = Graph()
    graph.add(owner)
    before = graph.value_hash(), len(graph.members)
    with pytest.raises(ValueError, match="owner's registry"):
        owner.parts.bind_owner(owner)
    assert fresh.registry is None
    assert (graph.value_hash(), len(graph.members)) == before


def test_vehicle_token_state_and_wallet_identity_survive_json() -> None:
    graph = Graph()
    vehicle = graph.add_node(kind=Vehicle, label="car")
    tires = VehicleComponent(label="tires", token_from="cheap_tires")
    vehicle.loadout.assign("tires", tires)
    tires.damage = 2
    wallet_id = vehicle.loadout.slot_wallet_ids["tires"]
    restored = Graph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    car = restored.get(vehicle.uid)
    restored_tires = restored.get(tires.uid)
    assert car.loadout.slot_wallet_ids["tires"] == wallet_id
    assert car.loadout.slot_wallet("tires") is restored.get(wallet_id)
    assert car.loadout.get_slot("tires")[0] is restored_tires
    assert restored_tires.damage == 2
    assert restored.value_hash() == graph.value_hash()


def test_frozen_graph_needs_a_prepared_slot() -> None:
    graph = StoryGraph(frozen_shape=True)
    owner = Machine(registry=graph)
    part = Component(label="part", registry=graph)
    before = graph.value_hash(), len(graph.members)
    assert not owner.parts.can_assign("left", part)[0]
    assert (graph.value_hash(), len(graph.members)) == before
    owner.parts.prepare_slot("left")
    owner.parts.assign("left", part)
    assert owner.parts.get_slot("left") == [part]
    empty = owner.parts.prepare_slot("empty")
    restored = StoryGraph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
    restored_owner = restored.get(owner.uid)
    assert restored_owner.parts.slot_wallet_ids["empty"] == empty.uid
    assert restored_owner.parts.slot_wallet("empty") is restored.get(empty.uid)
    assert restored_owner.parts.get_slot("empty") == []


def test_failed_offer_removes_new_group_and_registered_component() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    part = Component(label="new")
    before = graph.value_hash(), len(graph.members)
    offer = TransactionOffer(commitments=[
        ComponentAssignmentCommitment(owner.parts, "left", part),
        CallbackCommitment(label="fail", apply=lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
    ])
    with pytest.raises(RuntimeError, match="fail"):
        offer.accept()
    assert owner.parts.get_slot("left") == []
    assert part.registry is None and "left" not in owner.parts.slot_wallet_ids
    assert (graph.value_hash(), len(graph.members)) == before


def test_failed_slot_transfer_restores_source_order_and_removes_new_group() -> None:
    graph = Graph()
    source, target = Machine(registry=graph), Machine(registry=graph)
    first, second = Component(label="first", registry=graph), Component(label="second", registry=graph)
    source.parts.assign("left", first)
    source.parts.assign("left", second)
    before = graph.value_hash(), len(graph.members)
    offer = TransactionOffer(commitments=[
        AssetMoveCommitment(ComponentSlotAssetHolder(source.parts, "left"),
                            ComponentSlotAssetHolder(target.parts, "right"), first),
        CallbackCommitment(label="fail", apply=lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
    ])
    with pytest.raises(RuntimeError, match="fail"):
        offer.accept()
    assert source.parts.get_slot("left") == [first, second]
    assert "right" not in target.parts.slot_wallet_ids
    assert (graph.value_hash(), len(graph.members)) == before


def test_failed_catalog_offer_removes_automatically_registered_part() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    part = Component(label="new")
    before = graph.value_hash(), len(graph.members)
    offer = TransactionOffer(commitments=[
        CatalogAssetCommitment(ComponentSlotAssetHolder(owner.parts, "left"), lambda: part),
        CallbackCommitment(label="fail", apply=lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
    ])
    with pytest.raises(RuntimeError, match="fail"):
        offer.accept()
    assert part.registry is None and "left" not in owner.parts.slot_wallet_ids
    assert (graph.value_hash(), len(graph.members)) == before


def test_failed_offer_preserves_prepared_slot_order() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    owner.parts.prepare_slot("left")
    owner.parts.prepare_slot("right")
    before = dict(owner.parts.slot_wallet_ids)
    part = Component(label="part", registry=graph)
    offer = TransactionOffer(commitments=[
        ComponentAssignmentCommitment(owner.parts, "left", part),
        CallbackCommitment(label="fail", apply=lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
    ])
    with pytest.raises(RuntimeError, match="fail"):
        offer.accept()
    assert list(owner.parts.slot_wallet_ids.items()) == list(before.items())


def test_reoccupied_slot_returns_to_end_of_aggregate_order() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    owner.parts.prepare_slot("left")
    owner.parts.prepare_slot("right")
    first = Component(label="first", registry=graph)
    second = Component(label="second", registry=graph)
    owner.parts.assign("right", first)
    owner.parts.assign("left", second)
    assert owner.parts.all_components() == [first, second]
    owner.parts.unassign("right", first)
    owner.parts.assign("right", first)
    assert owner.parts.all_components() == [second, first]


def test_failed_replacement_restores_original_slot_alias() -> None:
    graph = Graph()
    owner = Machine(registry=graph)
    original = Component(label="original", registry=graph)
    replacement = Component(label="replacement", registry=graph)
    holder = ComponentSlotAssetHolder(owner.parts, "empty")
    holder.add_asset(original, label="special")
    before = graph.value_hash(), len(graph.members)
    offer = TransactionOffer(commitments=[
        ComponentAssignmentCommitment(owner.parts, "empty", replacement, allow_replace=True),
        CallbackCommitment(label="fail", apply=lambda: (_ for _ in ()).throw(RuntimeError("fail"))),
    ])
    with pytest.raises(RuntimeError, match="fail"):
        offer.accept()
    assert holder.get_asset("special") is original
    assert (graph.value_hash(), len(graph.members)) == before
