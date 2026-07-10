"""Persistence matrix tests for embedded component-manager graphs."""

from __future__ import annotations

import pytest
from pydantic import Field, model_validator

from tangl.core import Graph, Node, Selector
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CredentialComponent,
    CredentialDefinition,
    CredentialPacketManager,
)
from tangl.mechanics.credentials.domain import (
    ContrabandItem,
    Indication,
    Region,
)


class CredentialPacketOwner(Node):
    """Graph owner with an embedded component manager."""

    packet_manager: CredentialPacketManager = Field(
        default_factory=CredentialPacketManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_packet_owner(self) -> "CredentialPacketOwner":
        self.packet_manager.bind_owner(self)
        return self


@pytest.fixture(autouse=True)
def reset_credential_definitions():
    CredentialDefinition.clear_instances()
    yield
    CredentialDefinition.clear_instances()


def _definition(
    label: str,
    indication: Indication,
    *,
    document_kind: str = "document",
    requires_id: bool = False,
) -> CredentialDefinition:
    return CredentialDefinition(
        label=label,
        indication=indication,
        document_kind=document_kind,
        requires_id=requires_id,
    )


def _credential_graph() -> tuple[Graph, CredentialComponent, CredentialComponent]:
    id_definition = _definition(
        "matrix_id",
        Indication.TRAVEL,
        document_kind="id",
    )
    permit_definition = _definition(
        "matrix_work_permit",
        Indication.WORK,
        requires_id=True,
    )
    graph = Graph()
    owner = graph.add_node(kind=CredentialPacketOwner, label="checkpoint")
    id_card = graph.add_node(
        kind=CredentialComponent,
        label="matrix-id",
        token_from=id_definition.label,
    )
    work_permit = graph.add_node(
        kind=CredentialComponent,
        label="matrix-work-permit",
        token_from=permit_definition.label,
    )

    owner.packet_manager.region = Region.FOREIGN_EAST
    owner.packet_manager.purpose = Indication.WORK
    owner.packet_manager.possessions.append(
        ContrabandItem(indication=Indication.DRUGS, concealed=True)
    )
    owner.packet_manager.assign(CREDENTIAL_ID_SLOT, id_card)
    owner.packet_manager.assign(CREDENTIAL_PACKET_SLOT, work_permit)
    return graph, id_card, work_permit


def _load_graph(payload) -> Graph:
    if isinstance(payload, Graph):
        return payload
    if isinstance(payload, dict):
        return Graph.structure(dict(payload))
    raise TypeError(f"Unexpected payload type {type(payload)!r}")


def test_component_manager_graph_roundtrip_all_backends(manager) -> None:
    graph, id_card, work_permit = _credential_graph()

    manager.save(graph)
    restored = _load_graph(manager.load(graph.uid))
    owner = restored.find_one(Selector(label="checkpoint"))
    restored_id = restored.find_one(Selector(label="matrix-id"))
    restored_permit = restored.find_one(Selector(label="matrix-work-permit"))
    assert owner is not None
    assert restored_id is not None
    assert restored_permit is not None
    packet = owner.packet_manager

    assert packet.owner is owner
    assert packet.get_region() is Region.FOREIGN_EAST
    assert packet.get_purpose() is Indication.WORK
    assert packet.get_contraband() == [
        ContrabandItem(indication=Indication.DRUGS, concealed=True),
    ]
    assert packet.assignment_ids == {
        CREDENTIAL_ID_SLOT: [id_card.uid],
        CREDENTIAL_PACKET_SLOT: [work_permit.uid],
    }
    assert packet.get_slot(CREDENTIAL_ID_SLOT) == [restored_id]
    assert packet.get_slot(CREDENTIAL_PACKET_SLOT) == [restored_permit]
    assert sum(1 for item in restored.members.values() if item.uid == id_card.uid) == 1
    assert sum(1 for item in restored.members.values() if item.uid == work_permit.uid) == 1
