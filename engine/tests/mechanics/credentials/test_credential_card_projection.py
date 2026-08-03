"""Presentation-safe credential-card projection tests."""

from __future__ import annotations

import json

import pytest

from tangl.core import TokenCatalog
from tangl.mechanics.assembly import ComponentFacet
from tangl.mechanics.credentials import (
    CredentialCardProjection,
    CredentialDefinition,
    CredentialStatus,
    CredentialToken,
    Indication,
    Region,
    materialize_packet,
)
from tangl.mechanics.games import (
    CredentialPresentationProfile,
    CredentialsGame,
    CredentialsGameHandler,
)
from tangl.mechanics.games.credentials_game import CredentialCase


@pytest.fixture(autouse=True)
def clear_credential_definitions():
    CredentialDefinition.clear_instances()
    yield
    CredentialDefinition.clear_instances()


def _case(
    *,
    id_status: CredentialStatus = CredentialStatus.VALID,
    presented_documents: dict[str, str] | None = None,
    include_id: bool = True,
    include_requestable_permit: bool = False,
) -> CredentialCase:
    id_definition = CredentialDefinition(
        label="projection-id",
        name="Border Pass",
        indication=Indication.TRAVEL,
        document_kind="id",
        issuer_group="border_control",
        valid_period=0,
    )
    definitions = [id_definition] if include_id else []
    credentials: list[CredentialToken] = []
    if include_requestable_permit:
        definitions.append(
            CredentialDefinition(
                label="projection-permit",
                name="Travel Permit",
                indication=Indication.WORK,
                document_kind="document",
                issuer_group="border_control",
                valid_period=0,
                requires_id=True,
                facets=(
                    ComponentFacet(
                        channel="choice",
                        facet_type="giver",
                        payload="request_document",
                    ),
                ),
            )
        )
        credentials.append(
            CredentialToken(
                indication=Indication.WORK,
                status=CredentialStatus.MISSING_SEAL,
                requires_id=True,
            )
        )
    catalog = TokenCatalog(
        wst=CredentialDefinition,
        label="projection",
        members=tuple(definitions),
    )
    return CredentialCase(
        candidate_name="Ada Venn",
        presented_documents=presented_documents or {},
        packet_manager=materialize_packet(
            owner=object(),
            region=Region.LOCAL,
            purpose=Indication.TRAVEL,
            id_card=(
                CredentialToken(indication=Indication.TRAVEL, status=id_status)
                if include_id
                else None
            ),
            credentials=credentials,
            possessions=[],
            label_prefix="Ada Venn",
            catalog=catalog,
        ),
    )


def _game(
    case: CredentialCase,
    *,
    presentation: CredentialPresentationProfile | None = None,
) -> tuple[CredentialsGame, CredentialsGameHandler]:
    game = CredentialsGame(
        roster=[case],
        presentation=presentation or CredentialPresentationProfile(),
    )
    handler = CredentialsGameHandler()
    handler.setup(game)
    return game, handler


def test_id_projection_uses_canonical_component_case_labels_and_visible_order() -> None:
    game, handler = _game(_case())
    component = game.active_case.packet_manager.document_components()[0]

    projections = handler.credential_card_projections(game)

    assert len(projections) == 1
    assert projections[0].component_id == component.uid
    assert projections[0].subject_id == component.subject_id
    assert projections[0].document_kind == "id"
    assert projections[0].document_label == "passport"
    assert projections[0].bearer_label == "Ada Venn"
    assert [part.part_id for part in projections[0].visible_parts] == [
        "issuer_attestation",
        "validity",
    ]
    assert [part.content for part in projections[0].visible_parts] == [
        "A round blue border control seal is impressed beside the bearer line.",
        "The validity line reads “Valid through the current entry period.”",
    ]


@pytest.mark.parametrize(
    "status",
    [
        CredentialStatus.BAD_DATE,
        CredentialStatus.EXPIRED,
        CredentialStatus.MISSING_SEAL,
        CredentialStatus.FORGED,
        CredentialStatus.WRONG_HOLDER,
    ],
)
def test_projection_never_serializes_raw_evaluation_status(status: CredentialStatus) -> None:
    game, handler = _game(_case(id_status=status))

    payload = handler.credential_card_projections(game)[0].model_dump(mode="json")

    assert set(payload) == {
        "component_id",
        "subject_id",
        "document_kind",
        "document_label",
        "bearer_label",
        "visible_parts",
    }
    assert status.value not in json.dumps(payload)


def test_complete_authored_replacement_suppresses_card_projection() -> None:
    game, handler = _game(
        _case(presented_documents={"passport": "A hand-drawn credential."})
    )

    assert handler.credential_card_projections(game) == []


def test_unrelated_cleared_reissue_does_not_change_the_id_card_projection() -> None:
    game, handler = _game(_case(include_requestable_permit=True))
    before = handler.credential_card_projections(game)

    handler.receive_move(game, ("request_document", Indication.WORK.value))
    documents = handler._document_components(game)
    permit = next(document for document in documents if document.component.document_kind != "id")

    assert game.finding_status[Indication.WORK.value] == "cleared"
    assert [part.content for part in permit.visible_observations] == [
        "A round blue border control seal is impressed beside the bearer line.",
        "The validity line reads “Valid through the current entry period.”",
    ]
    assert handler.credential_card_projections(game) == before


def test_non_id_documents_do_not_produce_card_projections() -> None:
    game, handler = _game(_case(include_id=False, include_requestable_permit=True))

    assert handler.credential_card_projections(game) == []


def test_profiles_change_card_wording_without_changing_the_component() -> None:
    case = _case()
    first_game, first_handler = _game(case)
    first = first_handler.credential_card_projections(first_game)[0]
    second_game, second_handler = _game(
        case,
        presentation=CredentialPresentationProfile(
            identity_label="student ID",
            ordinary_attestation_template="A campus {issuer_group} stamp appears.",
            ordinary_validity_template="The date line is current.",
        ),
    )
    second = second_handler.credential_card_projections(second_game)[0]

    assert first.component_id == second.component_id
    assert first.document_label != second.document_label
    assert first.visible_parts != second.visible_parts


def test_projection_json_is_stable_and_presentation_safe() -> None:
    game, handler = _game(_case())
    projection = handler.credential_card_projections(game)[0]
    payload = {
        "component_id": str(projection.component_id),
        "subject_id": str(projection.subject_id),
        "document_kind": "id",
        "document_label": "passport",
        "bearer_label": "Ada Venn",
        "visible_parts": [
            {
                "part_id": "issuer_attestation",
                "content": "A round blue border control seal is impressed beside the bearer line.",
            },
            {
                "part_id": "validity",
                "content": "The validity line reads “Valid through the current entry period.”",
            },
        ],
    }

    assert projection.model_dump(mode="json") == payload
    assert CredentialCardProjection.model_validate(payload) == projection
