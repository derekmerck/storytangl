"""Neutral vehicle bay tests over transaction offer helpers."""

from __future__ import annotations

import pytest

from tangl.core import Graph, Selector
from tangl.mechanics.assembly.examples.vehicle import Vehicle
from tangl.mechanics.assembly.examples.vehicle_bay import (
    INSTALL_TIME_MINUTES,
    CatalogInstallCommitment,
    VehicleBay,
    build_catalog_install_offer,
    build_catalog_purchase_offer,
    build_inventory_install_offer,
    build_service_offer,
    component,
)
from tangl.mechanics.transaction import CallbackCommitment


def install_baseline(bay: VehicleBay) -> None:
    bay.vehicle.loadout.assign("chassis", component("mini_chassis"))
    bay.vehicle.loadout.assign("powerplant", component("cheap_powerplant"))
    bay.vehicle.loadout.assign("suspension", component("cheap_suspension"))
    bay.vehicle.loadout.assign("tires", component("cheap_tires"))


def test_vehicle_bay_service_offer_spends_cash_time_and_mutates_target() -> None:
    bay = VehicleBay(cash=500)
    tire = component("cheap_tires")
    tire.damage = 3

    offer = build_service_offer(
        bay,
        target=tire,
        field_name="damage",
        delta=-2,
        cash_cost=150,
        time_minutes=30,
        label="repair component damage",
    )
    receipt = offer.accept()

    assert bay.cash == 350
    assert bay.time_minutes == 30
    assert tire.damage == 1
    assert {detail["kind"] for detail in receipt.details} == {"value_delta"}
    assert {detail["label"] for detail in receipt.details} == {
        "cash",
        "time_minutes",
        "damage",
    }


def test_vehicle_bay_service_offer_rejects_insufficient_cash_before_mutation() -> None:
    bay = VehicleBay(cash=50)
    tire = component("cheap_tires")
    tire.damage = 3

    offer = build_service_offer(
        bay,
        target=tire,
        field_name="damage",
        delta=-1,
        cash_cost=150,
        label="repair component damage",
    )

    check = offer.can_accept()

    assert not check.accepted
    assert check.reason == "pay cash: value below minimum: -100 < 0"
    with pytest.raises(ValueError, match="pay cash"):
        offer.accept()
    assert bay.cash == 50
    assert bay.time_minutes == 0
    assert tire.damage == 3


def test_vehicle_bay_service_offer_rolls_back_after_late_failure() -> None:
    bay = VehicleBay(cash=500)
    tire = component("cheap_tires")
    tire.damage = 3

    def fail_after_service() -> None:
        raise RuntimeError("late service failure")

    offer = build_service_offer(
        bay,
        target=tire,
        field_name="damage",
        delta=-2,
        cash_cost=150,
        label="repair component damage",
        extra_commitments=[
            CallbackCommitment("fail after service", apply=fail_after_service),
        ],
    )

    with pytest.raises(RuntimeError, match="late service failure"):
        offer.accept()

    assert bay.cash == 500
    assert bay.time_minutes == 0
    assert tire.damage == 3


def test_vehicle_bay_installs_inventory_component() -> None:
    bay = VehicleBay(cash=1000)
    install_baseline(bay)
    old_tires = bay.vehicle.loadout.get_slot("tires")[0]
    bay.inventory.add_asset(component("slicks"))

    offer = build_inventory_install_offer(
        bay,
        component_key="slicks",
        slot_name="tires",
        price=350,
    )
    receipt = offer.accept()

    assert bay.cash == 650
    assert bay.time_minutes == INSTALL_TIME_MINUTES
    assert not bay.inventory.has_asset("slicks")
    assert bay.inventory.get_asset("cheap_tires") is old_tires
    assert bay.vehicle.loadout.get_slot("tires")[0].token_from == "slicks"
    assert {detail["kind"] for detail in receipt.details} >= {
        "asset_move",
        "component_assignment",
        "inventory_return",
        "value_delta",
    }


def test_vehicle_bay_stale_inventory_install_offer_returns_commit_time_replacement() -> None:
    bay = VehicleBay(cash=1000)
    bay.vehicle.loadout.assign("chassis", component("truck_chassis"))
    bay.vehicle.loadout.assign("powerplant", component("big_powerplant"))
    bay.vehicle.loadout.assign("suspension", component("cheap_suspension"))
    bay.vehicle.loadout.assign("tires", component("cheap_tires"))
    cheap_tires = bay.vehicle.loadout.get_slot("tires")[0]
    bay.inventory.add_asset(component("slicks"))
    bay.inventory.add_asset(component("all_terrain"))

    slicks_offer = build_inventory_install_offer(
        bay,
        component_key="slicks",
        slot_name="tires",
        price=0,
    )
    all_terrain_offer = build_inventory_install_offer(
        bay,
        component_key="all_terrain",
        slot_name="tires",
        price=0,
    )

    all_terrain_offer.accept()
    all_terrain = bay.vehicle.loadout.get_slot("tires")[0]
    slicks_offer.accept()

    assert bay.vehicle.loadout.get_slot("tires")[0].token_from == "slicks"
    assert bay.inventory.get_asset("all_terrain") is all_terrain
    assert bay.inventory.get_asset("cheap_tires") is cheap_tires
    assert not bay.inventory.has_asset("slicks")


def test_vehicle_bay_failed_inventory_install_keeps_cash_inventory_and_loadout() -> None:
    bay = VehicleBay(cash=1000)
    install_baseline(bay)
    bay.inventory.add_asset(component("slicks"))

    offer = build_inventory_install_offer(
        bay,
        component_key="slicks",
        slot_name="powerplant",
        price=350,
    )

    with pytest.raises(ValueError, match="Component doesn't match criteria"):
        offer.accept()

    assert bay.cash == 1000
    assert bay.time_minutes == 0
    assert bay.inventory.has_asset("slicks")
    assert bay.vehicle.loadout.get_slot("powerplant")[0].token_from == "cheap_powerplant"


def test_vehicle_bay_catalog_purchase_creates_graph_component_on_accept() -> None:
    graph = Graph()
    bay = VehicleBay(cash=1000)
    stock = {"slicks": 1}
    created = []

    def make_slicks():
        item = component("slicks")
        created.append(item)
        return item

    offer = build_catalog_purchase_offer(
        bay,
        label="slicks",
        price=350,
        supplier=make_slicks,
        registry=graph,
        stock=stock,
    )

    assert offer.can_accept().accepted
    assert created == []
    receipt = offer.accept()

    slicks = created[0]
    assert bay.cash == 650
    assert stock == {"slicks": 0}
    assert bay.inventory.get_asset("slicks") is slicks
    assert graph.get(slicks.uid) is slicks
    assert {detail["kind"] for detail in receipt.details} == {
        "catalog_asset",
        "mapping_delta",
        "value_delta",
    }


def test_vehicle_bay_catalog_purchase_rejects_unavailable_stock_before_creation() -> None:
    bay = VehicleBay(cash=1000)
    created = []

    def make_slicks():
        created.append(component("slicks"))
        return created[-1]

    offer = build_catalog_purchase_offer(
        bay,
        label="slicks",
        price=350,
        supplier=make_slicks,
        stock={"slicks": 0},
    )

    check = offer.can_accept()

    assert not check.accepted
    assert check.reason == "decrement catalog stock: value below minimum: -1 < 0"
    assert created == []
    assert bay.cash == 1000
    assert not bay.inventory.has_asset("slicks")


def test_vehicle_bay_catalog_purchase_rejects_duplicate_key_before_creation() -> None:
    bay = VehicleBay(cash=1000)
    bay.inventory.add_asset(component("slicks"))
    stock = {"slicks": 1}
    created = []

    def make_slicks():
        created.append(component("slicks"))
        return created[-1]

    offer = build_catalog_purchase_offer(
        bay,
        label="slicks",
        price=350,
        supplier=make_slicks,
        stock=stock,
    )

    check = offer.can_accept()

    assert not check.accepted
    assert check.reason == "create catalog asset: receiver already holds asset key"
    assert created == []
    assert bay.cash == 1000
    assert stock == {"slicks": 1}


def test_vehicle_bay_catalog_purchase_rolls_back_stock_and_inventory() -> None:
    graph = Graph()
    bay = VehicleBay(cash=1000)
    stock = {"slicks": 1}
    created = []

    def make_slicks():
        item = component("slicks")
        created.append(item)
        return item

    def fail_after_purchase() -> None:
        raise RuntimeError("late purchase failure")

    offer = build_catalog_purchase_offer(
        bay,
        label="slicks",
        price=350,
        supplier=make_slicks,
        registry=graph,
        stock=stock,
        extra_commitments=[
            CallbackCommitment("fail after purchase", apply=fail_after_purchase),
        ],
    )

    with pytest.raises(RuntimeError, match="late purchase failure"):
        offer.accept()

    slicks = created[0]
    assert bay.cash == 1000
    assert stock == {"slicks": 1}
    assert not bay.inventory.has_asset("slicks")
    assert graph.get(slicks.uid) is None


def test_vehicle_bay_catalog_install_creates_installs_and_round_trips_component() -> None:
    graph = Graph()
    vehicle = graph.add_node(label="demo-car", kind=Vehicle)
    bay = VehicleBay(vehicle=vehicle, cash=1000)
    install_baseline(bay)
    old_tires = bay.vehicle.loadout.get_slot("tires")[0]
    created = []

    def make_slicks():
        item = component("slicks")
        created.append(item)
        return item

    offer = build_catalog_install_offer(
        bay,
        label="slicks",
        slot_name="tires",
        price=350,
        supplier=make_slicks,
    )

    assert offer.can_accept().accepted
    assert created == []
    offer.accept()

    slicks = created[0]
    restored = Graph.structure(graph.unstructure())
    restored_vehicle = restored.find_one(Selector(label="demo-car"))
    restored_slicks = restored.get(slicks.uid)

    assert bay.cash == 650
    assert bay.time_minutes == INSTALL_TIME_MINUTES
    assert graph.get(slicks.uid) is slicks
    assert bay.inventory.get_asset("cheap_tires") is old_tires
    assert bay.vehicle.loadout.get_slot("tires") == [slicks]
    assert restored_vehicle.loadout.get_slot("tires") == [restored_slicks]


def test_vehicle_bay_catalog_install_rolls_back_after_late_failure() -> None:
    graph = Graph()
    vehicle = graph.add_node(label="demo-car", kind=Vehicle)
    bay = VehicleBay(vehicle=vehicle, cash=1000)
    install_baseline(bay)
    created = []
    starting_tires = list(bay.vehicle.loadout.get_slot("tires"))

    def make_slicks():
        item = component("slicks")
        created.append(item)
        return item

    def fail_after_install() -> None:
        raise RuntimeError("late install failure")

    offer = build_catalog_install_offer(
        bay,
        label="slicks",
        slot_name="tires",
        price=350,
        supplier=make_slicks,
        extra_commitments=[
            CallbackCommitment("fail after install", apply=fail_after_install),
        ],
    )

    with pytest.raises(RuntimeError, match="late install failure"):
        offer.accept()

    slicks = created[0]
    assert bay.cash == 1000
    assert bay.time_minutes == 0
    assert bay.vehicle.loadout.get_slot("tires") == starting_tires
    assert not bay.inventory.has_asset("cheap_tires")
    assert graph.get(slicks.uid) is None


def test_catalog_install_commitment_rolls_back_assignment_validation_failure() -> None:
    graph = Graph()
    vehicle = graph.add_node(label="demo-car", kind=Vehicle)
    bay = VehicleBay(vehicle=vehicle, cash=1000)
    install_baseline(bay)
    starting_tires = list(bay.vehicle.loadout.get_slot("tires"))
    created = []

    def make_truck_chassis():
        created.append(component("truck_chassis"))
        return created[-1]

    commitment = CatalogInstallCommitment(
        bay.vehicle.loadout,
        "tires",
        supplier=make_truck_chassis,
        preview=component("truck_chassis"),
        label="create invalid tires",
    )

    with pytest.raises(ValueError, match="Component doesn't match criteria"):
        commitment.commit()

    assert bay.vehicle.loadout.get_slot("tires") == starting_tires
    assert len(graph.members) == 5
    assert created == []


def test_catalog_install_commitment_rejects_supplier_preview_mismatch_without_graph_leak() -> None:
    graph = Graph()
    vehicle = graph.add_node(label="demo-car", kind=Vehicle)
    bay = VehicleBay(vehicle=vehicle, cash=1000)
    install_baseline(bay)
    starting_tires = list(bay.vehicle.loadout.get_slot("tires"))
    created = []

    def make_truck_chassis():
        created.append(component("truck_chassis"))
        return created[-1]

    commitment = CatalogInstallCommitment(
        bay.vehicle.loadout,
        "tires",
        supplier=make_truck_chassis,
        preview=component("slicks"),
        label="create mismatched tires",
    )

    assert commitment.can_commit().accepted
    with pytest.raises(ValueError, match="catalog supplier did not match preview"):
        commitment.commit()

    assert bay.vehicle.loadout.get_slot("tires") == starting_tires
    assert graph.get(created[0].uid) is None
