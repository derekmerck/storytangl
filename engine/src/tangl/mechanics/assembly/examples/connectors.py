from __future__ import annotations

from typing import ClassVar

from pydantic import Field, model_validator

from tangl.core import Node
from tangl.mechanics.assembly import ConnectionGroupManager, Connector, ConnectorPolarity, Slot


class DeviceConnectionGroup(ConnectionGroupManager):
    """Named connector group used by the neutral connection examples."""

    slots: ClassVar[dict[str, Slot]] = {
        "power": Slot.for_type("power", Connector, max_count=1),
        "video": Slot.for_type("video", Connector, max_count=1),
        "usb": Slot.for_type("usb", Connector, max_count=1),
        "end_a": Slot.for_type("end_a", Connector, max_count=1),
        "end_b": Slot.for_type("end_b", Connector, max_count=1),
        "port": Slot.for_type("port", Connector, max_count=1),
    }


class ConnectedDevice(Node):
    """Graph member with an embedded connector group manager."""

    connections: DeviceConnectionGroup = Field(
        default_factory=DeviceConnectionGroup,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_connection_owner(self) -> "ConnectedDevice":
        self.connections.bind_owner(self)
        return self

    def add_connector(self, slot_name: str, connector: Connector) -> Connector:
        self.connections.assign(slot_name, connector)
        return connector


def connector(label: str, shape: str, polarity: ConnectorPolarity) -> Connector:
    """Create one connector endpoint for examples and tests."""

    return Connector(
        label=label,
        connector_shape=shape,
        connector_polarity=polarity,
    )


def build_pc() -> ConnectedDevice:
    """Return a PC-like device that requires power, video, and USB connections."""

    device = ConnectedDevice(
        label="pc",
        connections=DeviceConnectionGroup(
            required_connection_slots={"power", "video", "usb"},
        ),
    )
    device.add_connector("power", connector("pc-power-socket", "power", "socket"))
    device.add_connector("video", connector("pc-video-socket", "video", "socket"))
    device.add_connector("usb", connector("pc-usb-socket", "usb", "socket"))
    return device


def build_pc_cable_bundle() -> ConnectedDevice:
    """Return a cable bundle with plugs matching the PC example."""

    device = ConnectedDevice(label="pc-cable-bundle")
    device.add_connector("power", connector("cable-power-plug", "power", "plug"))
    device.add_connector("video", connector("cable-video-plug", "video", "plug"))
    device.add_connector("usb", connector("cable-usb-plug", "usb", "plug"))
    return device


def build_monitor() -> ConnectedDevice:
    """Return a monitor-like peripheral requiring power and video."""

    device = ConnectedDevice(
        label="monitor",
        connections=DeviceConnectionGroup(required_connection_slots={"power", "video"}),
    )
    device.add_connector("power", connector("monitor-power-socket", "power", "socket"))
    device.add_connector("video", connector("monitor-video-socket", "video", "socket"))
    return device


def build_monitor_cable_bundle() -> ConnectedDevice:
    """Return a cable bundle with plugs matching the monitor example."""

    device = ConnectedDevice(label="monitor-cable-bundle")
    device.add_connector("power", connector("monitor-cable-power-plug", "power", "plug"))
    device.add_connector("video", connector("monitor-cable-video-plug", "video", "plug"))
    return device


__all__ = [
    "ConnectedDevice",
    "DeviceConnectionGroup",
    "build_monitor",
    "build_monitor_cable_bundle",
    "build_pc",
    "build_pc_cable_bundle",
    "connector",
]
