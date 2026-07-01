"""Transaction offer tests over the neutral vehicle assembly example."""

from __future__ import annotations

from typing import ClassVar

import pytest

from tangl.core import Graph, Node, Selector
from tangl.mechanics.assembly import ComponentManager, Slot
from tangl.mechanics.assembly.examples.vehicle import (
    Vehicle,
    VehicleComponent,
    VehicleLoadout,
    VehiclePartType,
)
from tangl.mechanics.progression import Stat
from tangl.mechanics.transaction import (
    CallbackCommitment,
    ComponentAssignmentCommitment,
    CountableTransferCommitment,
    MappingDeltaCommitment,
    RegistryAddCommitment,
    StatDeltaCommitment,
    TransactionCheck,
    TransactionOffer,
    TransactionRollbackError,
    ValueDeltaCommitment,
)
from tangl.story.concepts.asset import HasAssets


class GarageActor(HasAssets, Node):
    """Graph actor with a fungible wallet for transaction proof tests."""


class FailingCommitment:
    """Commitment test double that fails after preflight accepts."""

    label = "fail late"

    def can_commit(self) -> TransactionCheck:
        return TransactionCheck.accept()

    def commit(self) -> None:
        raise RuntimeError("late failure")

    def rollback(self) -> None:
        return None


class TrackingCommitment:
    """Commitment test double that records rollback attempts."""

    def __init__(self, label: str, *, fail_rollback: bool = False) -> None:
        self.label = label
        self.fail_rollback = fail_rollback
        self.rolled_back = False

    def can_commit(self) -> TransactionCheck:
        return TransactionCheck.accept()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        self.rolled_back = True
        if self.fail_rollback:
            raise RuntimeError(f"{self.label} rollback failed")


class BasicVehicleLoadout(ComponentManager[VehicleComponent]):
    """Single-slot manager without VehicleLoadout's replacement override."""

    slots: ClassVar[dict[str, Slot]] = {
        "tires": Slot.for_predicate(
            "tires",
            lambda component: (
                getattr(component, "part_type", None) is VehiclePartType.TIRES
            ),
        ),
    }


class RepairTarget:
    def __init__(self, hp: int, max_hp: int) -> None:
        self.hp = hp
        self.max_hp = max_hp


def part(label: str) -> VehicleComponent:
    return VehicleComponent(token_from=label, label=label)


def install_baseline(loadout: VehicleLoadout) -> None:
    loadout.assign("chassis", part("mini_chassis"))
    loadout.assign("powerplant", part("cheap_powerplant"))
    loadout.assign("suspension", part("cheap_suspension"))
    loadout.assign("tires", part("cheap_tires"))


def test_transaction_offer_rejects_invalid_payload_before_mutation() -> None:
    graph = Graph()
    buyer = graph.add_node(kind=GarageActor, label="buyer")
    shop = graph.add_node(kind=GarageActor, label="shop")
    vehicle = graph.add_node(kind=Vehicle, label="car")
    slicks = part("slicks")
    buyer.gain_countable("cash", 100)

    offer = TransactionOffer(
        label="buy impossible powerplant",
        commitments=[
            CountableTransferCommitment(buyer, shop, "cash", 350),
            RegistryAddCommitment(graph, slicks),
            ComponentAssignmentCommitment(vehicle.loadout, "powerplant", slicks),
        ],
    )

    check = offer.can_accept()

    assert not check.accepted
    assert check.reason == "transfer countable: giver cannot provide countable asset"
    assert buyer.wallet["cash"] == 100
    assert shop.wallet["cash"] == 0
    assert graph.get(slicks.uid) is None
    assert vehicle.loadout.get_slot("powerplant") == []

    with pytest.raises(ValueError, match="giver cannot provide countable asset"):
        offer.accept()


def test_transaction_offer_rolls_back_applied_commitments_after_late_failure() -> None:
    graph = Graph()
    buyer = graph.add_node(kind=GarageActor, label="buyer")
    shop = graph.add_node(kind=GarageActor, label="shop")
    tires = part("slicks")
    buyer.gain_countable("cash", 1000)

    offer = TransactionOffer(
        label="buy tires then fail",
        commitments=[
            CountableTransferCommitment(buyer, shop, "cash", 350),
            RegistryAddCommitment(graph, tires),
            FailingCommitment(),
        ],
    )

    with pytest.raises(RuntimeError, match="late failure"):
        offer.accept()

    assert buyer.wallet["cash"] == 1000
    assert shop.wallet["cash"] == 0
    assert graph.get(tires.uid) is None


def test_transaction_offer_attempts_all_rollbacks_before_reporting_failure() -> None:
    first = TrackingCommitment("first")
    second = TrackingCommitment("second", fail_rollback=True)
    offer = TransactionOffer(
        label="rollback failure",
        commitments=[
            first,
            second,
            FailingCommitment(),
        ],
    )

    with pytest.raises(TransactionRollbackError, match="second"):
        offer.accept()

    assert first.rolled_back
    assert second.rolled_back


def test_component_assignment_callable_supplier_resolves_once() -> None:
    graph = Graph()
    vehicle = graph.add_node(kind=Vehicle, label="car")
    created: list[VehicleComponent] = []

    def make_tires() -> VehicleComponent:
        component = part("slicks")
        created.append(component)
        return component

    offer = TransactionOffer(
        label="install generated tires",
        commitments=[
            ComponentAssignmentCommitment(vehicle.loadout, "tires", make_tires),
        ],
    )

    assert offer.can_accept().accepted
    offer.accept()

    assert len(created) == 1
    assert vehicle.loadout.get_slot("tires") == [created[0]]
    assert graph.get(created[0].uid) is created[0]


def test_component_assignment_allow_replace_works_for_base_manager() -> None:
    loadout = BasicVehicleLoadout()
    cheap_tires = part("cheap_tires")
    slicks = part("slicks")
    loadout.assign("tires", cheap_tires)

    offer = TransactionOffer(
        label="replace base-manager tires",
        commitments=[
            ComponentAssignmentCommitment(
                loadout,
                "tires",
                slicks,
                allow_replace=True,
            ),
        ],
    )

    assert offer.can_accept().accepted
    offer.accept()

    assert loadout.get_slot("tires") == [slicks]


def test_callback_commitment_binds_domain_local_inventory_moves() -> None:
    graph = Graph()
    vehicle = graph.add_node(kind=Vehicle, label="car")
    inventory = [part("slicks")]
    tires = inventory[0]

    def remove_from_inventory() -> dict[str, object]:
        inventory.remove(tires)
        return {"kind": "inventory_remove", "item_id": tires.uid}

    offer = TransactionOffer(
        label="install inventory tires",
        commitments=[
            CallbackCommitment(
                "remove from inventory",
                apply=remove_from_inventory,
                can_apply=lambda: tires in inventory,
                undo=lambda: inventory.append(tires),
            ),
            ComponentAssignmentCommitment(vehicle.loadout, "tires", tires),
        ],
    )

    receipt = offer.accept()

    assert inventory == []
    assert vehicle.loadout.get_slot("tires") == [tires]
    assert receipt.details[0]["kind"] == "inventory_remove"


def test_callback_commitment_rolls_back_domain_local_inventory_moves() -> None:
    graph = Graph()
    vehicle = graph.add_node(kind=Vehicle, label="car", max_price=50)
    inventory = [part("truck_chassis")]
    chassis = inventory[0]
    install_baseline(vehicle.loadout)

    offer = TransactionOffer(
        label="failed inventory install",
        commitments=[
            CallbackCommitment(
                "remove from inventory",
                apply=lambda: inventory.remove(chassis),
                can_apply=lambda: chassis in inventory,
                undo=lambda: inventory.append(chassis),
            ),
            ComponentAssignmentCommitment(
                vehicle.loadout,
                "chassis",
                chassis,
                validate_after=True,
                allow_replace=True,
            ),
        ],
    )

    with pytest.raises(ValueError, match="Price exceeds budget"):
        offer.accept()

    assert inventory == [chassis]
    assert vehicle.loadout.get_slot("chassis")[0].token_from == "mini_chassis"


def test_transaction_offer_buys_installs_and_round_trips_vehicle_component() -> None:
    graph = Graph()
    buyer = graph.add_node(kind=GarageActor, label="buyer")
    shop = graph.add_node(kind=GarageActor, label="shop")
    vehicle = graph.add_node(kind=Vehicle, label="car")
    tires = part("slicks")
    buyer.gain_countable("cash", 1000)
    install_baseline(vehicle.loadout)

    offer = TransactionOffer(
        label="buy and install slicks",
        commitments=[
            CountableTransferCommitment(buyer, shop, "cash", 350),
            RegistryAddCommitment(graph, tires),
            ComponentAssignmentCommitment(
                vehicle.loadout,
                "tires",
                tires,
                validate_after=True,
                allow_replace=True,
            ),
        ],
    )

    receipt = offer.accept()

    assert buyer.wallet["cash"] == 650
    assert shop.wallet["cash"] == 350
    assert graph.get(tires.uid) is tires
    assert vehicle.loadout.get_slot("tires") == [tires]
    assert receipt.offer_label == "buy and install slicks"
    assert receipt.commitment_labels == [
        "transfer countable",
        "add registry item",
        "assign component",
    ]

    restored = Graph.structure(graph.unstructure())
    restored_vehicle = restored.find_one(Selector(label="car"))
    restored_tires = restored.find_one(Selector(label="slicks"))

    assert restored_vehicle.loadout.owner is restored_vehicle
    assert restored_vehicle.loadout.get_slot("tires") == [restored_tires]
    assert restored_vehicle.loadout.validate() == []


def test_transaction_offer_rolls_back_component_assignment_validation_failure() -> None:
    graph = Graph()
    buyer = graph.add_node(kind=GarageActor, label="buyer")
    shop = graph.add_node(kind=GarageActor, label="shop")
    vehicle = graph.add_node(kind=Vehicle, label="car", max_price=800)
    truck_chassis = part("truck_chassis")
    buyer.gain_countable("cash", 3000)
    install_baseline(vehicle.loadout)

    offer = TransactionOffer(
        label="buy too expensive chassis",
        commitments=[
            CountableTransferCommitment(buyer, shop, "cash", 1600),
            ComponentAssignmentCommitment(
                vehicle.loadout,
                "chassis",
                truck_chassis,
                validate_after=True,
                allow_replace=True,
            ),
        ],
    )

    with pytest.raises(ValueError, match="Price exceeds budget"):
        offer.accept()

    assert buyer.wallet["cash"] == 3000
    assert shop.wallet["cash"] == 0
    assert graph.get(truck_chassis.uid) is None
    assert vehicle.loadout.get_slot("chassis")[0].token_from == "mini_chassis"


def test_value_delta_commitment_binds_repair_service_state() -> None:
    vehicle = RepairTarget(hp=3, max_hp=10)
    service = {"repair_capacity": 10}

    offer = TransactionOffer(
        label="repair vehicle",
        commitments=[
            MappingDeltaCommitment(service, "repair_capacity", -5),
            ValueDeltaCommitment(
                get_value=lambda: vehicle.hp,
                set_value=lambda value: setattr(vehicle, "hp", int(value)),
                delta=5,
                max_value=vehicle.max_hp,
                detail_label="vehicle.hp",
            ),
        ],
    )

    receipt = offer.accept()

    assert service["repair_capacity"] == 5
    assert vehicle.hp == 8
    assert receipt.details[0]["kind"] == "mapping_delta"
    assert receipt.details[1]["label"] == "vehicle.hp"


def test_value_delta_commitment_rejects_over_repair_before_mutation() -> None:
    vehicle = RepairTarget(hp=8, max_hp=10)
    service = {"repair_capacity": 10}

    offer = TransactionOffer(
        label="over repair vehicle",
        commitments=[
            MappingDeltaCommitment(service, "repair_capacity", -5),
            ValueDeltaCommitment(
                get_value=lambda: vehicle.hp,
                set_value=lambda value: setattr(vehicle, "hp", int(value)),
                delta=5,
                max_value=vehicle.max_hp,
                detail_label="vehicle.hp",
            ),
        ],
    )

    check = offer.can_accept()

    assert not check.accepted
    assert check.reason == "mutate value: value above maximum: 13 > 10"
    assert service["repair_capacity"] == 10
    assert vehicle.hp == 8


def test_mapping_delta_commitment_rolls_back_resource_mutations() -> None:
    station = {"fuel": 20}
    vehicle = {"fuel": 2}

    offer = TransactionOffer(
        label="refuel then fail",
        commitments=[
            MappingDeltaCommitment(station, "fuel", -8),
            MappingDeltaCommitment(vehicle, "fuel", 8, max_value=10),
            FailingCommitment(),
        ],
    )

    with pytest.raises(RuntimeError, match="late failure"):
        offer.accept()

    assert station["fuel"] == 20
    assert vehicle["fuel"] == 2


def test_mapping_delta_commitment_can_drop_zero_and_restore_missing_key() -> None:
    ammo = {"rockets": 2}
    station: dict[str, int] = {}

    offer = TransactionOffer(
        label="reload rockets",
        commitments=[
            MappingDeltaCommitment(ammo, "rockets", -2, drop_zero=True),
            MappingDeltaCommitment(station, "spent_rockets", 2),
            FailingCommitment(),
        ],
    )

    with pytest.raises(RuntimeError, match="late failure"):
        offer.accept()

    assert ammo == {"rockets": 2}
    assert station == {}


def test_stat_delta_commitment_mutates_progression_stat() -> None:
    patient = {"health": Stat(fv=50.0)}
    clinic = {"healing_capacity": 20}

    offer = TransactionOffer(
        label="heal patient",
        commitments=[
            MappingDeltaCommitment(clinic, "healing_capacity", -10),
            StatDeltaCommitment(
                patient,
                "health",
                10.0,
                min_value=0.0,
                max_value=100.0,
            ),
        ],
    )

    receipt = offer.accept()

    assert clinic["healing_capacity"] == 10
    assert patient["health"].fv == 60.0
    assert receipt.details[1]["kind"] == "stat_delta"
