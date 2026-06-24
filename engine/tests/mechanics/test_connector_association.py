"""Tests for connector association managers."""

from __future__ import annotations

from typing import ClassVar

import pytest

from tangl.core import Graph, Selector
from tangl.mechanics.assembly import ConnectionGroupManager, Connector, ConnectorPolarity, Slot
from tangl.mechanics.assembly.examples.connectors import (
    ConnectedDevice,
    DeviceConnectionGroup,
    build_pc,
    build_pc_cable_bundle,
    connector,
)
from tangl.persistence.serializers import JsonSerializationHandler


class ConnectionGroup(ConnectionGroupManager):
    slots: ClassVar[dict[str, Slot]] = {
        "a": Slot.for_type("a", Connector, max_count=1),
        "b": Slot.for_type("b", Connector, max_count=1),
    }


def endpoint(label: str, shape: str, polarity: ConnectorPolarity) -> Connector:
    return Connector(
        label=label,
        connector_shape=shape,
        connector_polarity=polarity,
    )


def test_connector_group_connects_matching_shape_and_opposite_polarity() -> None:
    group = ConnectionGroup()
    plug = endpoint("power-plug", "power", "plug")
    socket = endpoint("power-socket", "power", "socket")

    group.assign("a", plug)
    group.assign("b", socket)

    assert group.can_connect(plug, socket)

    group.connect(plug, socket)

    assert group.connected_to(plug) is socket
    assert group.connected_to(socket) is plug
    assert group.can_disconnect(plug, socket)

    group.disconnect(plug, socket)

    assert not group.is_connected(plug)
    assert not group.is_connected(socket)


def test_connector_group_rejects_incompatible_or_busy_endpoints() -> None:
    group = ConnectionGroup()
    plug = endpoint("power-plug", "power", "plug")
    second_plug = endpoint("second-power-plug", "power", "plug")
    video_socket = endpoint("video-socket", "video", "socket")
    power_socket = endpoint("power-socket", "power", "socket")

    assert not group.can_connect(plug, second_plug)
    assert not group.can_connect(plug, video_socket)

    group.connect(plug, power_socket)

    assert not group.can_connect(plug, video_socket)
    assert not group.can_connect(second_plug, power_socket)
    assert not group.can_disconnect(second_plug, power_socket)

    with pytest.raises(ValueError):
        group.connect(second_plug, power_socket)

    with pytest.raises(ValueError):
        group.disconnect(second_plug, power_socket)


def test_connector_group_requires_disconnect_before_unassign() -> None:
    group = ConnectionGroup()
    plug = endpoint("power-plug", "power", "plug")
    socket = endpoint("power-socket", "power", "socket")

    group.assign("a", plug)
    group.assign("b", socket)
    group.connect(plug, socket)

    with pytest.raises(ValueError):
        group.unassign("a", plug)

    group.disconnect(plug, socket)
    group.unassign("a", plug)

    assert group.get_slot("a") == []


def test_connector_group_registers_assigned_connectors_with_owner_graph() -> None:
    graph = Graph()
    owner = graph.add_node(kind=ConnectedDevice, label="hub")
    plug = Connector(label="usb-plug", connector_shape="usb", connector_polarity="plug")

    owner.connections.assign("usb", plug)

    assert graph.get(plug.uid) is plug
    assert owner.connections.get_slot("usb") == [plug]


def test_prebuilt_connection_group_registers_connectors_when_owner_enters_graph() -> None:
    graph = Graph()
    pc = build_pc()

    graph.add(pc)
    restored = Graph.structure(graph.unstructure())
    restored_pc = restored.find_one(Selector(label="pc"))
    restored_power = restored.find_one(Selector(label="pc-power-socket"))

    assert restored_power is not None
    assert restored_pc.connections.owner is restored_pc
    assert restored_pc.connections.get_slot("power") == [restored_power]


def test_connector_group_rejects_connections_across_owner_registries() -> None:
    first_graph = Graph()
    second_graph = Graph()
    pc = first_graph.add_node(kind=ConnectedDevice, label="pc")
    cable = second_graph.add_node(kind=ConnectedDevice, label="cable")
    pc_power = pc.add_connector("power", endpoint("pc-power-socket", "power", "socket"))
    cable_power = cable.add_connector("power", endpoint("cable-power-plug", "power", "plug"))

    assert not pc.connections.can_connect(
        pc_power,
        cable_power,
        other_manager=cable.connections,
    )

    with pytest.raises(ValueError):
        pc.connections.connect(pc_power, cable_power, other_manager=cable.connections)


def test_connector_group_roundtrip_preserves_pair_ids() -> None:
    graph = Graph()
    pc = graph.add_node(
        kind=ConnectedDevice,
        label="pc",
        connections=DeviceConnectionGroup(required_connection_slots={"power"}),
    )
    cable = graph.add_node(kind=ConnectedDevice, label="cable")
    pc_power = graph.add_node(
        kind=Connector,
        label="pc-power-socket",
        connector_shape="power",
        connector_polarity="socket",
    )
    cable_power = graph.add_node(
        kind=Connector,
        label="cable-power-plug",
        connector_shape="power",
        connector_polarity="plug",
    )

    pc.add_connector("power", pc_power)
    cable.add_connector("power", cable_power)
    pc.connections.connect(pc_power, cable_power, other_manager=cable.connections)

    restored = Graph.structure(graph.unstructure())
    restored_pc = restored.find_one(Selector(label="pc"))
    restored_cable = restored.find_one(Selector(label="cable"))
    restored_pc_power = restored.find_one(Selector(label="pc-power-socket"))
    restored_cable_power = restored.find_one(Selector(label="cable-power-plug"))

    assert restored_pc.connections.owner is restored_pc
    assert restored_cable.connections.owner is restored_cable
    assert restored_pc.connections.connection_ids == {pc_power.uid: cable_power.uid}
    assert restored_cable.connections.connection_ids == {cable_power.uid: pc_power.uid}
    assert restored_pc.connections.connected_to(restored_pc_power) is restored_cable_power
    assert restored_cable.connections.connected_to(restored_cable_power) is restored_pc_power
    assert restored_pc.connections.is_complete


def test_connection_ids_are_json_safe_constructor_form() -> None:
    group = ConnectionGroup()
    plug = endpoint("power-plug", "power", "plug")
    socket = endpoint("power-socket", "power", "socket")

    group.assign("a", plug)
    group.assign("b", socket)
    group.connect(plug, socket)

    data = group.unstructure()
    JsonSerializationHandler.serialize(data)
    restored = ConnectionGroup.structure(data)

    assert data["connection_ids"] == {
        str(plug.uid): str(socket.uid),
        str(socket.uid): str(plug.uid),
    }
    assert restored.connection_ids == {
        plug.uid: socket.uid,
        socket.uid: plug.uid,
    }


def test_disconnect_drops_remote_cache_entries() -> None:
    pc = ConnectedDevice(label="pc")
    cable = ConnectedDevice(label="cable")
    pc_power = pc.add_connector("power", endpoint("pc-power-socket", "power", "socket"))
    cable_power = cable.add_connector("power", endpoint("cable-power-plug", "power", "plug"))

    pc.connections.connect(pc_power, cable_power, other_manager=cable.connections)

    assert cable_power.uid in pc.connections._component_cache
    assert pc_power.uid in cable.connections._component_cache

    pc.connections.disconnect(pc_power, cable_power, other_manager=cable.connections)

    assert pc_power.uid in pc.connections._component_cache
    assert cable_power.uid not in pc.connections._component_cache
    assert cable_power.uid in cable.connections._component_cache
    assert pc_power.uid not in cable.connections._component_cache


def test_pc_like_connection_group_completes_against_matching_cable_bundle() -> None:
    pc = build_pc()
    cable_bundle = build_pc_cable_bundle()

    assert not pc.connections.is_complete
    assert pc.connections.can_connect_group(cable_bundle.connections)

    pairings = pc.connections.connect_group(cable_bundle.connections)

    assert [left.connector_shape for left, _right in pairings] == ["power", "video", "usb"]
    assert pc.connections.is_complete


def test_pc_like_connection_group_rejects_incomplete_cable_bundle() -> None:
    pc = build_pc()
    cable_bundle = ConnectedDevice(label="incomplete-cable-bundle")
    cable_bundle.add_connector("power", connector("cable-power-plug", "power", "plug"))

    assert not pc.connections.can_connect_group(cable_bundle.connections)

    with pytest.raises(ValueError):
        pc.connections.connect_group(cable_bundle.connections)


def test_required_connection_slots_must_have_connectors() -> None:
    pc = ConnectedDevice(
        label="pc",
        connections=DeviceConnectionGroup(required_connection_slots={"power"}),
    )
    cable_bundle = build_pc_cable_bundle()

    assert not pc.connections.is_complete
    assert not pc.connections.can_connect_group(cable_bundle.connections)

    with pytest.raises(ValueError):
        pc.connections.connect_group(cable_bundle.connections)
