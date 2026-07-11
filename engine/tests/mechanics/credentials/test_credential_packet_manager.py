"""Tests for assembly-backed credential packet managers."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import Field, model_validator

from tangl.core import Graph, Node, Selector
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CredentialComponent,
    CredentialDefinition,
    CredentialPacketManager as AssemblyCredentialPacketManager,
    ensure_default_credential_definitions,
)
from tangl.mechanics.credentials.domain import (
    ContrabandItem,
    CredentialStatus,
    CredentialToken,
    Indication,
    Region,
    Restrictions,
    RestrictionLevel,
)
from tangl.mechanics.games import HasGame
from tangl.mechanics.games.credentials_game import (
    CredentialCase,
    CredentialDisposition,
    CredentialsGame,
    CredentialsGameHandler,
    derive_disposition,
)
from tangl.mechanics.games.credentials_roster import ScenarioOffer
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.story import Block

D = CredentialDisposition
S = CredentialStatus
IND = Indication
L = RestrictionLevel

LOCAL_RULES = Restrictions.from_map(
    {
        Region.LOCAL: {
            IND.TRAVEL: L.WITH_ID,
            IND.WORK: L.WITH_PERMIT,
            IND.EMIGRATE: L.ANONYMOUS,
            IND.WEAPON: L.WITH_PERMIT,
            IND.DRUGS: L.FORBIDDEN,
            IND.SECRETS: L.FORBIDDEN,
        }
    }
)


@pytest.fixture(autouse=True)
def reset_credential_definitions():
    CredentialDefinition.clear_instances()
    yield
    CredentialDefinition.clear_instances()


class CredentialsBlock(HasGame, Block):
    """Test block embedding the credential shift."""

    _game_class = CredentialsGame
    _game_handler_class = CredentialsGameHandler


CredentialsBlock.model_rebuild(_types_namespace={"UUID": UUID})


class CredentialPacketNode(Node):
    """Graph owner used to prove packet manager constructor-form persistence."""

    packet_manager: AssemblyCredentialPacketManager = Field(
        default_factory=AssemblyCredentialPacketManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_packet_owner(self) -> "CredentialPacketNode":
        self.packet_manager.bind_owner(self)
        return self


def credential_definition(
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


def credential_component(
    label: str,
    definition: CredentialDefinition,
    *,
    status: CredentialStatus = CredentialStatus.VALID,
    holder_matches: bool = True,
) -> CredentialComponent:
    return CredentialComponent(
        label=label,
        token_from=definition.label,
        status=status,
        holder_matches=holder_matches,
    )


def valid_work_packet() -> tuple[
    AssemblyCredentialPacketManager,
    CredentialComponent,
    CredentialComponent,
]:
    id_definition = credential_definition(
        "checkpoint_id",
        IND.TRAVEL,
        document_kind="id",
    )
    permit_definition = credential_definition(
        "work_permit",
        IND.WORK,
        requires_id=True,
    )
    id_card = credential_component("candidate-id", id_definition)
    work_permit = credential_component("candidate-work-permit", permit_definition)
    manager = AssemblyCredentialPacketManager(purpose=IND.WORK)
    manager.assign(CREDENTIAL_ID_SLOT, id_card)
    manager.assign(CREDENTIAL_PACKET_SLOT, work_permit)
    return manager, id_card, work_permit


def test_assembly_packet_projects_legacy_discovery_surface() -> None:
    manager, id_card, work_permit = valid_work_packet()

    assert manager.get_region() is Region.LOCAL
    assert manager.get_purpose() is IND.WORK
    assert manager.id_status() is S.VALID
    assert manager.credential_for(IND.WORK) == CredentialToken(
        indication=IND.WORK,
        requires_id=True,
    )
    assert manager.all_credentials() == [
        id_card.to_credential_token(),
        work_permit.to_credential_token(),
    ]
    assert derive_disposition(manager, LOCAL_RULES) is D.PASS


def test_credential_case_delegates_to_owned_assembly_packet() -> None:
    manager, _, _ = valid_work_packet()
    case = CredentialCase(packet_manager=manager)

    assert case.get_purpose() is IND.WORK
    assert case.id_status() is S.VALID
    assert case.credential_for(IND.WORK) == CredentialToken(
        indication=IND.WORK,
        requires_id=True,
    )
    assert case.to_packet_manager() is manager
    assert derive_disposition(case, LOCAL_RULES) is D.PASS


def test_assembly_packet_preserves_failure_parity() -> None:
    manager, _, work_permit = valid_work_packet()
    work_permit.status = S.FORGED
    case = CredentialCase(packet_manager=manager)

    assert derive_disposition(manager, LOCAL_RULES) is D.ARREST
    assert derive_disposition(case, LOCAL_RULES) is D.ARREST


def test_packet_manager_keeps_contraband_value_shaped_for_now() -> None:
    manager, _, _ = valid_work_packet()
    manager.possessions.append(ContrabandItem(indication=IND.DRUGS, concealed=False))

    assert manager.get_contraband() == [
        ContrabandItem(indication=IND.DRUGS, concealed=False),
    ]
    assert derive_disposition(manager, LOCAL_RULES) is D.DENY


def test_packet_manager_constructor_form_is_json_safe() -> None:
    manager = AssemblyCredentialPacketManager(
        region=Region.FOREIGN_EAST,
        purpose=IND.WORK,
        possessions=[ContrabandItem(indication=IND.DRUGS)],
    )

    payload = JsonSerializationHandler.deserialize(
        JsonSerializationHandler.serialize(manager.unstructure())
    )
    restored = AssemblyCredentialPacketManager.structure(payload)

    assert payload["region"] == Region.FOREIGN_EAST.value
    assert payload["purpose"] == IND.WORK.value
    assert payload["possessions"] == [{"indication": IND.DRUGS.value}]
    assert restored.get_region() is Region.FOREIGN_EAST
    assert restored.get_purpose() is IND.WORK
    assert restored.get_contraband() == [ContrabandItem(indication=IND.DRUGS)]


def test_packet_manager_graph_roundtrip_preserves_credential_assignments_by_id() -> None:
    id_definition = credential_definition(
        "roundtrip_id",
        IND.TRAVEL,
        document_kind="id",
    )
    permit_definition = credential_definition(
        "roundtrip_work_permit",
        IND.WORK,
        requires_id=True,
    )
    graph = Graph()
    owner = graph.add_node(kind=CredentialPacketNode, label="checkpoint")
    id_card = graph.add_node(
        kind=CredentialComponent,
        label="roundtrip-id",
        token_from=id_definition.label,
    )
    work_permit = graph.add_node(
        kind=CredentialComponent,
        label="roundtrip-work-permit",
        token_from=permit_definition.label,
    )
    manager = owner.packet_manager
    manager.purpose = IND.WORK
    manager.assign(CREDENTIAL_ID_SLOT, id_card)
    manager.assign(CREDENTIAL_PACKET_SLOT, work_permit)

    restored = Graph.structure(graph.unstructure())
    restored_owner = restored.find_one(Selector(label="checkpoint"))
    restored_manager = restored_owner.packet_manager
    restored_id = restored.find_one(Selector(label="roundtrip-id"))
    restored_permit = restored.find_one(Selector(label="roundtrip-work-permit"))

    assert restored_manager.owner is restored_owner
    assert restored_manager.assignment_ids == {
        CREDENTIAL_ID_SLOT: [id_card.uid],
        CREDENTIAL_PACKET_SLOT: [work_permit.uid],
    }
    assert restored_manager.get_slot(CREDENTIAL_ID_SLOT) == [restored_id]
    assert restored_manager.get_slot(CREDENTIAL_PACKET_SLOT) == [restored_permit]
    assert derive_disposition(restored_manager, LOCAL_RULES) is D.PASS
    assert sum(1 for item in restored.members.values() if item.uid == id_card.uid) == 1
    assert sum(1 for item in restored.members.values() if item.uid == work_permit.uid) == 1


def test_has_game_block_binds_roster_packet_manager_to_graph_owner() -> None:
    id_definition = credential_definition(
        "block_id",
        IND.TRAVEL,
        document_kind="id",
    )
    permit_definition = credential_definition(
        "block_work_permit",
        IND.WORK,
        requires_id=True,
    )
    graph = Graph()
    block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
    id_card = graph.add_node(
        kind=CredentialComponent,
        label="block-id",
        token_from=id_definition.label,
    )
    work_permit = graph.add_node(
        kind=CredentialComponent,
        label="block-work-permit",
        token_from=permit_definition.label,
    )
    manager = AssemblyCredentialPacketManager(purpose=IND.WORK)
    manager.assign(CREDENTIAL_ID_SLOT, id_card)
    manager.assign(CREDENTIAL_PACKET_SLOT, work_permit)
    block.game_state = CredentialsGame(
        roster=[CredentialCase(candidate_name="Mara", packet_manager=manager)],
        restriction_map=LOCAL_RULES,
    )

    restored_manager = block.game.roster[0].packet_manager

    assert restored_manager is manager
    assert restored_manager.owner is block
    assert restored_manager.get_slot(CREDENTIAL_ID_SLOT) == [id_card]
    assert restored_manager.get_slot(CREDENTIAL_PACKET_SLOT) == [work_permit]


def test_has_game_structure_binds_roster_packet_manager_to_restored_owner() -> None:
    manager = AssemblyCredentialPacketManager(purpose=IND.WORK)
    block = CredentialsBlock(label="checkpoint")
    block.game_state = CredentialsGame(
        roster=[CredentialCase(candidate_name="Mara", packet_manager=manager)],
        restriction_map=LOCAL_RULES,
    )

    restored = CredentialsBlock.structure(block.unstructure())
    restored_manager = restored.game.roster[0].packet_manager

    assert restored_manager is not None
    assert restored_manager.owner is restored


def test_has_game_binds_pinned_offer_packet_manager_before_materialization() -> None:
    id_definition = credential_definition(
        "pinned_id",
        IND.TRAVEL,
        document_kind="id",
    )
    graph = Graph()
    block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
    id_card = graph.add_node(
        kind=CredentialComponent,
        label="pinned-id",
        token_from=id_definition.label,
    )
    manager = AssemblyCredentialPacketManager(purpose=IND.TRAVEL)
    manager.assign(CREDENTIAL_ID_SLOT, id_card)
    pinned_case = CredentialCase(candidate_name="Pinned", packet_manager=manager)
    block.game_state = CredentialsGame(
        offers=[ScenarioOffer(candidate_name="Pinned", pinned_case=pinned_case)],
        restriction_map=LOCAL_RULES,
    )

    active_case = block.game.active_case
    restored_manager = active_case.packet_manager

    assert active_case is pinned_case
    assert restored_manager is manager
    assert restored_manager.owner is block
    assert restored_manager.get_slot(CREDENTIAL_ID_SLOT) == [id_card]


def test_sampled_offers_materialize_once_at_game_lifecycle_boundaries() -> None:
    graph = Graph()
    block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
    block.game_state = CredentialsGame(
        offers=[
            ScenarioOffer(
                candidate_name="Mara",
                region=Region.LOCAL,
                purpose=IND.WORK,
            ),
            ScenarioOffer(
                candidate_name="Tomas",
                region=Region.LOCAL,
                purpose=IND.TRAVEL,
            ),
        ],
        restriction_map=LOCAL_RULES,
    )
    handler = block.game_handler
    handler.setup(block.game)

    first_case = block.game.active_case
    first_packet = first_case.packet_manager
    assert first_packet is not None
    assert first_packet.owner is block
    assert first_case.id_card is None
    assert first_case.packet == []
    assert first_packet.get_slot(CREDENTIAL_ID_SLOT)
    assert first_packet.get_slot(CREDENTIAL_PACKET_SLOT)
    component_count = sum(
        isinstance(item, CredentialComponent)
        for item in graph.members.values()
    )

    assert handler.get_available_moves(block.game)
    assert (
        sum(isinstance(item, CredentialComponent) for item in graph.members.values())
        == component_count
    )

    handler.receive_move(block.game, ("inspect", "passport"))
    handler.receive_move(block.game, ("decide", "pass"))

    second_case = block.game.active_case
    assert second_case.candidate_name == "Tomas"
    assert second_case.packet_manager is not None
    assert second_case.packet_manager.owner is block
    assert (
        sum(isinstance(item, CredentialComponent) for item in graph.members.values())
        > component_count
    )


def test_sampled_packet_graph_roundtrip_keeps_component_references() -> None:
    graph = Graph()
    block = graph.add_node(kind=CredentialsBlock, label="checkpoint")
    block.game_state = CredentialsGame(
        offers=[
            ScenarioOffer(
                candidate_name="Mara",
                region=Region.LOCAL,
                purpose=IND.WORK,
            ),
        ],
        restriction_map=LOCAL_RULES,
    )
    block.game_handler.setup(block.game)
    packet = block.game.active_case.packet_manager
    assert packet is not None
    component_ids = {
        component.uid
        for slot_name in (CREDENTIAL_ID_SLOT, CREDENTIAL_PACKET_SLOT)
        for component in packet.get_slot(slot_name)
    }

    payload = graph.unstructure()
    CredentialDefinition.clear_instances()
    ensure_default_credential_definitions()
    restored = Graph.structure(payload)
    restored_block = restored.find_one(Selector(label="checkpoint"))
    restored_packet = restored_block.game.active_case.packet_manager

    assert restored_packet is not None
    assert restored_packet.owner is restored_block
    assert {
        component.uid
        for slot_name in (CREDENTIAL_ID_SLOT, CREDENTIAL_PACKET_SLOT)
        for component in restored_packet.get_slot(slot_name)
    } == component_ids
    assert (
        sum(item.uid in component_ids for item in restored.members.values())
        == len(component_ids)
    )


def test_binding_a_prepared_game_materializes_its_cached_sample() -> None:
    game = CredentialsGame(
        offers=[
            ScenarioOffer(
                candidate_name="Mara",
                region=Region.LOCAL,
                purpose=IND.WORK,
            ),
        ],
        restriction_map=LOCAL_RULES,
    )
    handler = CredentialsGameHandler()
    handler.setup(game)
    cached_case = game.active_case
    assert cached_case.packet_manager is None

    graph = Graph()
    block = graph.add_node(kind=CredentialsBlock, label="checkpoint", game_state=game)
    packet = block.game.active_case.packet_manager

    assert packet is not None
    assert packet.owner is block
    assert packet.get_slot(CREDENTIAL_ID_SLOT)
    assert packet.get_slot(CREDENTIAL_PACKET_SLOT)
