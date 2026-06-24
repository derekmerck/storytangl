from __future__ import annotations

from uuid import UUID

from pydantic import Field

from tangl.type_hints import UnstructuredData

from .base import ComponentManager
from .component import Connector


class ConnectionGroupManager(ComponentManager[Connector]):
    """Owner-bound manager for connector endpoints and their pairwise associations."""

    connection_ids: dict[UUID, UUID] = Field(default_factory=dict)
    required_connection_slots: set[str] = Field(default_factory=set)

    def _connectors_in_order(self) -> list[Connector]:
        connectors: list[Connector] = []
        slot_names = list(self.slots)
        slot_names.extend(name for name in self._slot_names() if name not in self.slots)
        for slot_name in slot_names:
            connectors.extend(self.get_slot(slot_name))
        return connectors

    def _required_slot_names(self) -> list[str]:
        if self.required_connection_slots:
            return [
                name
                for name in self.slots
                if name in self.required_connection_slots
            ]
        return [name for name, slot in self.slots.items() if slot.required]

    def required_connectors(self) -> list[Connector]:
        connectors: list[Connector] = []
        for slot_name in self._required_slot_names():
            connectors.extend(self.get_slot(slot_name))
        return connectors

    def _has_required_slot_assignments(self) -> bool:
        return all(
            self._has_slot_components(slot_name)
            for slot_name in self._required_slot_names()
        )

    def _drop_unassigned_cache(self, connector_id: UUID) -> None:
        if not any(connector_id in ids for ids in self.assignment_ids.values()):
            self._component_cache.pop(connector_id, None)

    def is_connected(self, connector: Connector) -> bool:
        return connector.uid in self.connection_ids

    def connected_to(self, connector: Connector) -> Connector | None:
        peer_id = self.connection_ids.get(connector.uid)
        if peer_id is None:
            return None
        return self._resolve_component(peer_id)

    def unassign(self, slot_name: str, component: Connector) -> None:
        if self.is_connected(component):
            raise ValueError(f"Cannot unassign connected connector {component.label!r}")
        super().unassign(slot_name, component)

    @staticmethod
    def _compatible(first: Connector, second: Connector) -> bool:
        return (
            first.uid != second.uid
            and first.connector_shape == second.connector_shape
            and first.connector_polarity != second.connector_polarity
        )

    def can_connect(
        self,
        first: Connector,
        second: Connector,
        *,
        other_manager: "ConnectionGroupManager | None" = None,
    ) -> bool:
        second_manager = other_manager or self
        return (
            self._compatible(first, second)
            and not self.is_connected(first)
            and not second_manager.is_connected(second)
        )

    def connect(
        self,
        first: Connector,
        second: Connector,
        *,
        other_manager: "ConnectionGroupManager | None" = None,
    ) -> None:
        second_manager = other_manager or self
        if not self.can_connect(first, second, other_manager=other_manager):
            raise ValueError(f"Cannot connect {first.label!r} to {second.label!r}")

        self._validate_component_registry(first)
        second_manager._validate_component_registry(second)
        self._component_cache[first.uid] = first
        self._component_cache[second.uid] = second
        second_manager._component_cache[second.uid] = second
        second_manager._component_cache[first.uid] = first

        self.connection_ids[first.uid] = second.uid
        second_manager.connection_ids[second.uid] = first.uid

    def can_disconnect(
        self,
        first: Connector,
        second: Connector,
        *,
        other_manager: "ConnectionGroupManager | None" = None,
    ) -> bool:
        second_manager = other_manager or self
        return (
            self.connection_ids.get(first.uid) == second.uid
            and second_manager.connection_ids.get(second.uid) == first.uid
        )

    def disconnect(
        self,
        first: Connector,
        second: Connector,
        *,
        other_manager: "ConnectionGroupManager | None" = None,
    ) -> None:
        second_manager = other_manager or self
        if not self.can_disconnect(first, second, other_manager=other_manager):
            raise ValueError(f"Cannot disconnect {first.label!r} from {second.label!r}")
        self.connection_ids.pop(first.uid, None)
        second_manager.connection_ids.pop(second.uid, None)
        self._drop_unassigned_cache(second.uid)
        second_manager._drop_unassigned_cache(first.uid)

    def _find_group_pairings(
        self,
        other_manager: "ConnectionGroupManager",
    ) -> list[tuple[Connector, Connector]]:
        if not self._has_required_slot_assignments():
            return []
        pairings: list[tuple[Connector, Connector]] = []
        used_remote: set[UUID] = set()
        for connector in self.required_connectors():
            if self.is_connected(connector):
                continue
            match = next(
                (
                    candidate
                    for candidate in other_manager._connectors_in_order()
                    if candidate.uid not in used_remote
                    and self.can_connect(
                        connector,
                        candidate,
                        other_manager=other_manager,
                    )
                ),
                None,
            )
            if match is None:
                return []
            pairings.append((connector, match))
            used_remote.add(match.uid)
        return pairings

    def can_connect_group(self, other_manager: "ConnectionGroupManager") -> bool:
        if not self._has_required_slot_assignments():
            return False
        unconnected_required = [
            connector
            for connector in self.required_connectors()
            if not self.is_connected(connector)
        ]
        if not unconnected_required:
            return True
        return len(self._find_group_pairings(other_manager)) == len(unconnected_required)

    def connect_group(
        self,
        other_manager: "ConnectionGroupManager",
    ) -> list[tuple[Connector, Connector]]:
        if not self._has_required_slot_assignments():
            raise ValueError("Connection group cannot satisfy all required connectors")
        pairings = self._find_group_pairings(other_manager)
        unconnected_required = [
            connector
            for connector in self.required_connectors()
            if not self.is_connected(connector)
        ]
        if len(pairings) != len(unconnected_required):
            raise ValueError("Connection group cannot satisfy all required connectors")
        for first, second in pairings:
            self.connect(first, second, other_manager=other_manager)
        return pairings

    @property
    def is_complete(self) -> bool:
        if not self._has_required_slot_assignments():
            return False
        return all(self.is_connected(connector) for connector in self.required_connectors())

    def unstructure(self) -> UnstructuredData:
        data = super().unstructure()
        if self.connection_ids:
            data["connection_ids"] = self.connection_ids
        if self.required_connection_slots:
            data["required_connection_slots"] = sorted(self.required_connection_slots)
        return data
