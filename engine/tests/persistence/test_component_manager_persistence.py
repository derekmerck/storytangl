"""Persistence matrix tests for embedded component-manager graphs."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import Field, model_validator

from tangl.core import Graph, Node, Selector
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.persistence import PersistenceManagerFactory
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CREDENTIAL_PACKET_SLOT,
    CredentialComponent,
    CredentialDefinition,
    CredentialPacketManager,
)
from tangl.mechanics.credentials.domain import (
    ContrabandItem,
    CredentialStatus,
    Indication,
    Region,
)
from tangl.mechanics.sandbox import SandboxScope
from tangl.story import World


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
def reset_credential_definitions() -> Iterator[None]:
    CredentialDefinition.clear_instances()
    World.clear_instances()
    yield
    CredentialDefinition.clear_instances()
    World.clear_instances()


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


def _credential_graph() -> tuple[
    Graph,
    CredentialComponent,
    CredentialComponent,
    CredentialComponent,
]:
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
    second_work_permit = graph.add_node(
        kind=CredentialComponent,
        label="matrix-work-permit-second",
        token_from=permit_definition.label,
    )

    id_card.status = CredentialStatus.EXPIRED
    owner.packet_manager.region = Region.FOREIGN_EAST
    owner.packet_manager.purpose = Indication.WORK
    owner.packet_manager.possessions.append(
        ContrabandItem(indication=Indication.DRUGS, concealed=True)
    )
    owner.packet_manager.assign(CREDENTIAL_ID_SLOT, id_card)
    owner.packet_manager.assign(CREDENTIAL_PACKET_SLOT, work_permit)
    owner.packet_manager.assign(CREDENTIAL_PACKET_SLOT, second_work_permit)
    return graph, id_card, work_permit, second_work_permit


def _compile_scoped_credential_world(
    root: Path,
    *,
    label: str,
    pass_name: str,
) -> World:
    package = root / label
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "domain.py").write_text(
        "from tangl.mechanics.credentials import CredentialDefinition\n",
        encoding="utf-8",
    )
    (root / "world.yaml").write_text(
        f"""label: {label}
scripts: script.yaml
domain_module: {label}.domain
assets:
  - asset_kind: CredentialDefinition
    catalog: school
    source: credential_types.yaml
""",
        encoding="utf-8",
    )
    (root / "script.yaml").write_text(
        f"""label: {label}
metadata:
  title: {label}
scenes:
  hall:
    blocks:
      entrance:
        content: A student approaches.
""",
        encoding="utf-8",
    )
    (root / "credential_types.yaml").write_text(
        f"""activity_pass:
  name: {pass_name}
  origin_ids: [lower_school]
  indication: activity
  document_kind: document
  requires_id: false
""",
        encoding="utf-8",
    )
    return WorldCompiler().compile(WorldBundle.load(root))


def _catalog_definition(world: World, catalog_id: str) -> CredentialDefinition:
    catalog = world.assets.values["school"]
    definition = next(
        member for member in catalog.members if member.catalog_id == catalog_id
    )
    assert isinstance(definition, CredentialDefinition)
    return definition


def _load_graph(payload) -> Graph:
    if isinstance(payload, Graph):
        return payload
    if isinstance(payload, dict):
        return Graph.structure(dict(payload))
    raise TypeError(f"Unexpected payload type {type(payload)!r}")


def test_component_manager_graph_roundtrip_all_backends(manager) -> None:
    graph, id_card, work_permit, second_work_permit = _credential_graph()

    manager.save(graph)
    restored = _load_graph(manager.load(graph.uid))
    owner = restored.find_one(Selector(label="checkpoint"))
    restored_id = restored.find_one(Selector(label="matrix-id"))
    restored_permit = restored.find_one(Selector(label="matrix-work-permit"))
    restored_second_permit = restored.find_one(
        Selector(label="matrix-work-permit-second")
    )
    assert owner is not None
    assert restored_id is not None
    assert restored_permit is not None
    assert restored_second_permit is not None
    packet = owner.packet_manager

    assert packet.owner is owner
    assert packet.get_region() == Region.FOREIGN_EAST
    assert packet.get_purpose() == Indication.WORK
    assert packet.get_contraband() == [
        ContrabandItem(indication=Indication.DRUGS, concealed=True),
    ]
    assert packet.assignment_ids == {
        CREDENTIAL_ID_SLOT: [id_card.uid],
        CREDENTIAL_PACKET_SLOT: [work_permit.uid, second_work_permit.uid],
    }
    assert packet.get_slot(CREDENTIAL_ID_SLOT) == [restored_id]
    assert packet.get_slot(CREDENTIAL_PACKET_SLOT) == [
        restored_permit,
        restored_second_permit,
    ]
    assert restored.get(id_card.uid) is restored_id
    assert restored_id.token_from == id_card.token_from
    assert restored_id.reference_singleton is CredentialDefinition.get_instance(
        "matrix_id"
    )
    assert restored_id.status is CredentialStatus.EXPIRED
    assert sum(1 for item in restored.members.values() if item.uid == id_card.uid) == 1
    assert sum(1 for item in restored.members.values() if item.uid == work_permit.uid) == 1
    assert sum(1 for item in restored.members.values() if item.uid == second_work_permit.uid) == 1


def test_has_assets_wallet_survives_json_file_persistence(tmp_path: Path) -> None:
    graph = Graph()
    scope = graph.add_node(kind=SandboxScope, label="wallet-scope")
    scope.player_assets.wallet.gain(coins=7)
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path)

    persistence.save(graph)
    restored = _load_graph(persistence.load(graph.uid))
    restored_scope = restored.find_one(Selector(label="wallet-scope"))

    assert isinstance(restored_scope, SandboxScope)
    assert restored_scope.player_assets.wallet.amounts == {"coins": 7}


def test_json_roundtrip_rebinds_tokens_to_their_world_catalog(tmp_path: Path) -> None:
    north_root = tmp_path / "north_school"
    south_root = tmp_path / "south_school"
    north = _compile_scoped_credential_world(
        north_root,
        label="north_school",
        pass_name="North activity pass",
    )
    south = _compile_scoped_credential_world(
        south_root,
        label="south_school",
        pass_name="South activity pass",
    )
    north_definition = _catalog_definition(north, "activity_pass")
    south_definition = _catalog_definition(south, "activity_pass")
    assert north_definition is not south_definition

    graph = Graph(factory=north)
    owner = graph.add_node(kind=CredentialPacketOwner, label="checkpoint")
    pass_token = graph.add_node(
        kind=CredentialComponent,
        label="north-activity-pass",
        token_from="activity_pass",
    )
    pass_token.status = CredentialStatus.EXPIRED
    owner.packet_manager.assign(CREDENTIAL_PACKET_SLOT, pass_token)

    south_graph = Graph(factory=south)
    south_token = south_graph.add_node(
        kind=CredentialComponent,
        label="south-activity-pass",
        token_from="activity_pass",
    )
    assert pass_token.reference_singleton is north_definition
    assert south_token.reference_singleton is south_definition
    assert pass_token.reference_singleton is not south_token.reference_singleton

    foreign_token = CredentialComponent(
        label="foreign-activity-pass",
        token_from=south_definition.label,
    )
    with pytest.raises(LookupError, match="No CredentialDefinition definition"):
        graph.add(foreign_token)

    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "store")
    persistence.save(graph)

    CredentialDefinition.clear_instances()
    World.clear_instances()
    restored_north = _compile_scoped_credential_world(
        north_root,
        label="north_school",
        pass_name="North activity pass",
    )
    restored = _load_graph(persistence.load(graph.uid))
    restored_owner = restored.find_one(Selector(label="checkpoint"))
    restored_token = restored.find_one(Selector(label="north-activity-pass"))

    assert isinstance(restored_owner, CredentialPacketOwner)
    assert isinstance(restored_token, CredentialComponent)
    assert restored.factory is restored_north
    assert restored_token.uid == pass_token.uid
    assert restored.get(pass_token.uid) is restored_token
    assert restored_owner.packet_manager.owner is restored_owner
    assert restored_owner.packet_manager.get_slot(CREDENTIAL_PACKET_SLOT) == [
        restored_token,
    ]
    assert restored_token.token_from == "activity_pass"
    assert restored_token.reference_singleton is _catalog_definition(
        restored_north,
        "activity_pass",
    )
    assert restored_token.status is CredentialStatus.EXPIRED
    assert sum(
        item.uid == restored_token.uid for item in restored.members.values()
    ) == 1
