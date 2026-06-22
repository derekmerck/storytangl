"""Vehicle example tests for owner-bound loadout managers."""

from __future__ import annotations

from tangl.core import Graph, Selector
from tangl.mechanics.assembly.examples.vehicle import (
    Vehicle,
    VehicleComponent,
    VehicleLoadout,
)


def part(label: str) -> VehicleComponent:
    return VehicleComponent(token_from=label, label=label)


def install_baseline(loadout: VehicleLoadout) -> None:
    loadout.assign("chassis", part("mini_chassis"))
    loadout.assign("powerplant", part("cheap_powerplant"))
    loadout.assign("suspension", part("cheap_suspension"))
    loadout.assign("tires", part("cheap_tires"))


def test_vehicle_component_label_uses_reference_label() -> None:
    component = VehicleComponent(token_from="cheap_tires", label="local-token")

    assert component.get_label() == "cheap_tires"


def test_vehicle_loadout_requires_named_slots() -> None:
    vehicle = Vehicle(label="test-car")

    assert vehicle.loadout.validate() == [
        "Required slot empty: chassis",
        "Required slot empty: powerplant",
        "Required slot empty: suspension",
        "Required slot empty: tires",
    ]

    install_baseline(vehicle.loadout)

    assert vehicle.loadout.validate() == []


def test_vehicle_description_warns_for_missing_required_parts() -> None:
    vehicle = Vehicle(label="test-car")
    loadout = vehicle.loadout

    loadout.assign("chassis", part("mini_chassis"))
    loadout.assign("powerplant", part("cheap_powerplant"))
    loadout.assign("suspension", part("cheap_suspension"))

    assert vehicle.describe_vehicle() == (
        "a vehicle built on a mini chassis, powered by a cheap powerplant, "
        "and riding on cheap suspension. Warning: missing tires."
    )


def test_vehicle_loadout_replaces_single_slot_occupant() -> None:
    vehicle = Vehicle(label="test-car")
    loadout = vehicle.loadout

    loadout.assign("tires", part("cheap_tires"))
    cheap_tires = loadout.get_slot("tires")[0]

    loadout.assign("tires", part("slicks"))
    installed_tires = loadout.get_slot("tires")

    assert len(installed_tires) == 1
    assert installed_tires[0].token_from == "slicks"
    assert cheap_tires.uid not in loadout.assignment_ids["tires"]


def test_heavy_vehicle_requires_big_powerplant() -> None:
    vehicle = Vehicle(label="hauler")
    loadout = vehicle.loadout

    loadout.assign("chassis", part("truck_chassis"))
    loadout.assign("powerplant", part("cheap_powerplant"))
    loadout.assign("suspension", part("off_road_suspension"))
    loadout.assign("tires", part("all_terrain"))

    assert "Powerplant output too low: 45.0 < 90.0" in loadout.validate()
    assert vehicle.describe_vehicle() == (
        "a vehicle built on a truck chassis, powered by a cheap powerplant, "
        "riding on off road suspension, and with all terrain. "
        "Warning: powerplant output is too low."
    )

    loadout.assign("powerplant", part("big_powerplant"))

    assert loadout.validate() == []


def test_vehicle_price_budget_validation() -> None:
    vehicle = Vehicle(label="too-fancy", max_price=3000)
    loadout = vehicle.loadout

    loadout.assign("chassis", part("truck_chassis"))
    loadout.assign("powerplant", part("big_powerplant"))
    loadout.assign("suspension", part("racing_suspension"))
    loadout.assign("tires", part("slicks"))

    assert "Price exceeds budget: 3850.0 > 3000.0" in loadout.validate()


def test_vehicle_loadout_describes_installed_components() -> None:
    vehicle = Vehicle(label="demo")
    install_baseline(vehicle.loadout)

    namespace = vehicle.get_ns()

    assert vehicle.describe_vehicle() == (
        "a vehicle built on a mini chassis, powered by a cheap powerplant, "
        "riding on cheap suspension, and with cheap tires"
    )
    assert namespace["vehicle_description"] == vehicle.describe_vehicle()
    assert namespace["vehicle_component_tokens"] == [
        "chassis: mini chassis",
        "powerplant: cheap powerplant",
        "suspension: cheap suspension",
        "tires: cheap tires",
    ]


def test_vehicle_graph_roundtrip_preserves_loadout_assignments_by_graph_id() -> None:
    graph = Graph()
    vehicle = graph.add_node(kind=Vehicle, label="demo-car")
    chassis = graph.add_node(
        kind=VehicleComponent,
        label="demo-chassis",
        token_from="mid_chassis",
    )
    powerplant = graph.add_node(
        kind=VehicleComponent,
        label="demo-powerplant",
        token_from="cheap_powerplant",
    )
    suspension = graph.add_node(
        kind=VehicleComponent,
        label="demo-suspension",
        token_from="cheap_suspension",
    )
    tires = graph.add_node(
        kind=VehicleComponent,
        label="demo-tires",
        token_from="cheap_tires",
    )

    vehicle.loadout.assign("chassis", chassis)
    vehicle.loadout.assign("powerplant", powerplant)
    vehicle.loadout.assign("suspension", suspension)
    vehicle.loadout.assign("tires", tires)

    vehicle_data = vehicle.unstructure()
    restored = Graph.structure(graph.unstructure())
    restored_vehicle = restored.find_one(Selector(label="demo-car"))
    restored_tires = restored.find_one(Selector(label="demo-tires"))

    assert vehicle_data["loadout"]["assignment_ids"] == {
        "chassis": [chassis.uid],
        "powerplant": [powerplant.uid],
        "suspension": [suspension.uid],
        "tires": [tires.uid],
    }
    assert restored_vehicle.loadout.owner is restored_vehicle
    assert restored_vehicle.loadout.get_slot("tires") == [restored_tires]
    assert restored_vehicle.loadout.validate() == []
    assert restored_vehicle.describe_vehicle() == (
        "a vehicle built on a mid chassis, powered by a cheap powerplant, "
        "riding on cheap suspension, and with cheap tires"
    )
    assert sum(1 for item in restored.members.values() if item.uid == tires.uid) == 1
