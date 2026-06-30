"""Transaction offer tests over the neutral vehicle assembly example."""

from __future__ import annotations

import pytest

from tangl.core import Graph, Node, Selector
from tangl.mechanics.assembly.examples.vehicle import (
    Vehicle,
    VehicleComponent,
    VehicleLoadout,
)
from tangl.mechanics.transaction import (
    ComponentAssignmentCommitment,
    CountableTransferCommitment,
    RegistryAddCommitment,
    TransactionCheck,
    TransactionOffer,
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
            RegistryAddCommitment(graph, truck_chassis),
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
