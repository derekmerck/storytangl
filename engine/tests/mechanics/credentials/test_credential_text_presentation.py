"""Narrative projection tests for graph-backed credential documents."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import Field, model_validator

from tangl.core import BehaviorRegistry, DispatchLayer, Graph, Node, Selector
from tangl.mechanics.credentials import (
    CREDENTIAL_ID_SLOT,
    CredentialComponent,
    CredentialDefinition,
    CredentialPacketManager,
    CredentialStatus,
    Indication,
)
from tangl.mechanics.games import CredentialsGame, HasGame
from tangl.mechanics.games.credentials_game import CredentialCase
from tangl.mechanics.presence.look import HairColor, HairStyle, Look, SkinTone
from tangl.story import Block
from tangl.story.presentation import render_text_as
from tangl.vm.runtime.frame import PhaseCtx


class _TextCtx:
    cursor = SimpleNamespace(label="credential-presentation")

    def __init__(self, authorities: list[BehaviorRegistry] | None = None) -> None:
        self.authorities = authorities or []

    def get_ns(self, _source: object | None = None) -> dict[str, object]:
        return {}

    def get_authorities(self) -> list[BehaviorRegistry]:
        return self.authorities

    def get_inline_behaviors(self) -> list[object]:
        return []


class CredentialPacketOwner(Node):
    """Graph owner for one embedded credential packet in presentation tests."""

    packet_manager: CredentialPacketManager = Field(
        default_factory=CredentialPacketManager,
        json_schema_extra={"include": True, "unstructurable": True},
    )

    @model_validator(mode="after")
    def _bind_packet_owner(self) -> "CredentialPacketOwner":
        self.packet_manager.bind_owner(self)
        return self


CredentialPacketOwner.model_rebuild(_types_namespace={"UUID": UUID})


class CredentialsBlock(HasGame, Block):
    """Story host for a credentials game namespace integration test."""

    _game_class = CredentialsGame


CredentialsBlock.model_rebuild(_types_namespace={"UUID": UUID})


@pytest.fixture(autouse=True)
def _reset_credential_definitions():
    CredentialDefinition.clear_instances()
    yield
    CredentialDefinition.clear_instances()


def _look(hair_color: HairColor) -> Look:
    return Look(
        hair_color=hair_color,
        hair_style=HairStyle.LONG,
        skin_tone=SkinTone.OLIVE,
    )


def _identity_document_graph(
    *,
    name: str | None = "travel passport",
) -> tuple[Graph, CredentialPacketOwner, CredentialComponent]:
    definition = CredentialDefinition(
        label="presentation_id",
        name=name,
        indication=Indication.TRAVEL,
        document_kind="id",
    )
    graph = Graph()
    owner = graph.add_node(kind=CredentialPacketOwner, label="checkpoint")
    packet = owner.packet_manager
    packet.bind_owner(owner)
    bearer = packet.resolve_subject(packet.bearer_id)
    bearer.look = _look(HairColor.RED)
    document = graph.add_node(
        kind=CredentialComponent,
        label="candidate-id",
        token_from=definition.label,
        subject_id=packet.bearer_id,
    )
    packet.assign(CREDENTIAL_ID_SLOT, document)
    return graph, owner, document


def _render_document(
    document: CredentialComponent,
    packet: CredentialPacketManager,
    *,
    ctx: _TextCtx | None = None,
) -> str:
    return render_text_as(
        document,
        "document_description",
        ctx=ctx or _TextCtx(),
        bindings={"packet": packet},
    )


def test_graph_bound_identity_document_renders_its_named_subject() -> None:
    _, owner, document = _identity_document_graph()

    rendered = _render_document(document, owner.packet_manager)

    assert "travel passport" in rendered
    assert "olive skin" in rendered
    assert "red long hair" in rendered


def test_document_renders_from_the_hosted_credentials_namespace() -> None:
    definition = CredentialDefinition(
        label="hosted_presentation_id",
        name="travel passport",
        indication=Indication.TRAVEL,
        document_kind="id",
    )
    manager = CredentialPacketManager()
    game = CredentialsGame(roster=[CredentialCase(packet_manager=manager)])
    graph = Graph()
    block = graph.add_node(
        kind=CredentialsBlock,
        label="checkpoint",
        game_state=game,
    )
    packet = block.game.active_case.packet_manager
    bearer = packet.resolve_subject(packet.bearer_id)
    bearer.look = _look(HairColor.RED)
    document = graph.add_node(
        kind=CredentialComponent,
        label="hosted-candidate-id",
        token_from=definition.label,
        subject_id=packet.bearer_id,
    )
    packet.assign(CREDENTIAL_ID_SLOT, document)
    ctx = PhaseCtx(graph=graph, cursor_id=block.uid)

    assert ctx.get_ns(block)["packet"] is packet
    assert "red long hair" in render_text_as(document, "document_description", ctx=ctx)


def test_identity_document_uses_a_neutral_fallback_name() -> None:
    _, owner, document = _identity_document_graph(name=None)

    assert "identity document" in _render_document(document, owner.packet_manager)


def test_candidate_and_document_share_one_subject_when_their_uuids_match() -> None:
    _, owner, document = _identity_document_graph()
    packet = owner.packet_manager
    bearer = packet.resolve_subject(packet.bearer_id)

    candidate = render_text_as(bearer, "presence_description", ctx=_TextCtx())
    document_description = _render_document(document, packet)

    assert document.subject_id == packet.bearer_id == bearer.uid
    assert "red long hair" in candidate
    assert "red long hair" in document_description


def test_mismatched_subjects_render_visible_facts_without_validity_language() -> None:
    _, owner, document = _identity_document_graph()
    packet = owner.packet_manager
    recorded_subject = packet.materialize_subject("recorded-subject")
    recorded_subject.look = _look(HairColor.BLUE)
    document.subject_id = recorded_subject.uid

    candidate = render_text_as(
        packet.resolve_subject(packet.bearer_id),
        "presence_description",
        ctx=_TextCtx(),
    )
    document_description = _render_document(document, packet)

    assert document.subject_id != packet.bearer_id
    assert "red long hair" in candidate
    assert "blue long hair" in document_description
    assert not any(
        forbidden in document_description.lower()
        for forbidden in ("wrong holder", "invalid", "valid", "forged", "arrest", "deny")
    )


def test_document_projection_reads_live_subject_state_and_ignores_status() -> None:
    _, owner, document = _identity_document_graph()
    packet = owner.packet_manager
    subject = packet.resolve_subject(document.subject_id)
    initial = _render_document(document, packet)

    subject.look.hair_color = HairColor.BLUE
    updated = _render_document(document, packet)
    document.status = CredentialStatus.FORGED
    status_changed = _render_document(document, packet)

    assert "red long hair" in initial
    assert "blue long hair" in updated
    assert status_changed == updated


def test_authority_can_reskin_the_document_without_changing_its_component() -> None:
    _, owner, document = _identity_document_graph()
    authority = BehaviorRegistry(
        label="credential-presentation-author",
        default_dispatch_layer=DispatchLayer.AUTHOR,
    )

    authority.register(
        lambda **_kwargs: "student ID, bearing a campus portrait",
        task="render_text",
        wants_caller_kind=CredentialComponent,
        wants_exact_kind=False,
    )

    assert _render_document(
        document,
        owner.packet_manager,
        ctx=_TextCtx(authorities=[authority]),
    ) == "student ID, bearing a campus portrait"


def test_unresolved_document_subject_fails_explicitly() -> None:
    _, owner, document = _identity_document_graph()
    document.subject_id = uuid4()

    with pytest.raises(KeyError, match="not a presence entity"):
        _render_document(document, owner.packet_manager)


def test_document_rendering_preserves_graph_constructor_form_state() -> None:
    graph, owner, document = _identity_document_graph()
    before = graph.unstructure()

    _render_document(document, owner.packet_manager)

    assert graph.unstructure() == before


def test_document_subject_binding_and_projection_survive_graph_roundtrip() -> None:
    graph, owner, document = _identity_document_graph()
    before = _render_document(document, owner.packet_manager)

    restored = Graph.structure(graph.unstructure())
    restored_owner = restored.find_one(Selector(label="checkpoint"))
    restored_document = restored.find_one(Selector(label="candidate-id"))
    restored_packet = restored_owner.packet_manager
    after = _render_document(restored_document, restored_packet)

    assert restored_document.uid == document.uid
    assert restored_document.subject_id == document.subject_id
    assert restored_packet.bearer_id == owner.packet_manager.bearer_id
    assert restored_packet.resolve_subject(restored_document.subject_id).uid == document.subject_id
    assert after == before
